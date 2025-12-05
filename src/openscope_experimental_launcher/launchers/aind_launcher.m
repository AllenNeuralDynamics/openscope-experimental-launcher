function aind_launcher(varargin)
%AIND_LAUNCHER Share the current MATLAB engine for OpenScope launchers.
%   AIND_LAUNCHER() registers the running MATLAB session using
%   matlab.engine.shareEngine so that the Python OpenScope launcher can
%   attach with matlab.engine.connect_matlab.  A simple UI window is also
%   created so the experimenter can notify Python when MATLAB processing is
%   finished.

if nargin >= 1
    firstArg = varargin{1};
    if ischar(firstArg) || isstring(firstArg)
        firstText = lower(string(firstArg));
        if firstText == "execute"
            varargin(1) = [];
            aind_launcher_execute(varargin{:});
            return;
        end
    end
end

if nargin < 1 || isempty(varargin{1})
    engineName = 'openscope_launcher';
else
    engineName = varargin{1};
end

alreadyShared = false;
try
    matlab.engine.shareEngine(engineName);
    fprintf('[OpenScope] Shared MATLAB engine ''%s''.\n', engineName);
catch err
    if contains(lower(err.message), 'already shared')
        alreadyShared = true;
        fprintf('[OpenScope] MATLAB engine already shared as ''%s''.\n', engineName);
    else
        rethrow(err);
    end
end

if alreadyShared
    try
        existingEngines = matlab.engine.enginename;
        if isempty(existingEngines)
            fprintf('[OpenScope] MATLAB reports no active shared engines.\n');
        else
            fprintf('[OpenScope] MATLAB shared engines: %s\n', strjoin(existingEngines, ', '));
        end
    catch enumerationErr
        warning('OpenScope:MatlabLauncher:EngineEnumerationFailed', ...
            'Unable to enumerate shared MATLAB engines: %s', enumerationErr.message);
    end
end

fig = openscope_aind_get_ui();
openscope_aind_update_status(fig, sprintf('Waiting for Python launcher (engine: %s)...', engineName));
assignin('base', 'OPENSCOPE_LAUNCHER_COMPLETED', false);
end


function aind_launcher_execute(acquisitionFunction, varargin)
%AIND_LAUNCHER_EXECUTE Run a MATLAB acquisition entry point for OpenScope.
%   This helper is invoked from Python after the engine connection is
%   established.  It executes the supplied MATLAB function (either a handle
%   or name) and holds at a completion prompt so the user can signal when
%   MATLAB is finished.  Additional arguments are forwarded directly to the
%   acquisition function.

if nargin < 1 || isempty(acquisitionFunction)
    error('Acquisition function handle or name is required.');
end

fig = openscope_aind_get_ui();

[resumeMode, varargin] = openscope_aind_extract_resume_flag(varargin);

openscope_aind_set_completion_enabled(fig, false);

if resumeMode
    openscope_aind_prepare_for_resume(fig, acquisitionFunction);
else
    openscope_aind_set_resume_visible(fig, false);
end

openscope_aind_update_status(fig, sprintf('Running %s ...', openscope_aind_function_label(acquisitionFunction)));

sessionFolder = '';
if ~isempty(varargin)
    firstArg = varargin{1};
    if ischar(firstArg) || isstring(firstArg)
        candidate = char(firstArg);
        if isfolder(candidate)
            sessionFolder = candidate;
            assignin('base', 'OPENSCOPE_SESSION_FOLDER', sessionFolder);
            varargin(1) = [];
        end
    end
end

originalDir = pwd;
restoreDir = onCleanup(@() cd(originalDir)); %#ok<NASGU>

if ~isempty(sessionFolder)
    try
        cd(sessionFolder);
    catch dirErr
        warning('OpenScope:MatlabLauncher:ChangeDirFailed', ...
            'Failed to change directory to session folder "%s": %s', sessionFolder, dirErr.message);
    end
end

acquisitionHandle = openscope_aind_resolve_function(acquisitionFunction);

try
    feval(acquisitionHandle, varargin{:});
catch err
    openscope_aind_update_status(fig, ['Error: ' err.message]);
    openscope_aind_set_completion_enabled(fig, true);
    rethrow(err);
end

openscope_aind_update_status(fig, 'Acquisition complete. Press "Signal Acquisition Complete" when ready to continue.');
openscope_aind_set_completion_enabled(fig, true);
uiwait(fig);
end


function fig = openscope_aind_get_ui()
%OPEN_SCOPE_AIND_GET_UI Create or return the shared UI figure.

persistent storedFig

if isempty(storedFig) || ~isvalid(storedFig)
    storedFig = uifigure('Name', 'OpenScope MATLAB Launcher', ...
        'Position', [100 100 420 180]);
    storedFig.CloseRequestFcn = @(src, evt)openscope_aind_close_request(src);

    layout = uigridlayout(storedFig, [3 1]);
    layout.RowHeight = {'1x', 45, 45};
    layout.Padding = [12 12 12 12];
    layout.RowSpacing = 12;

    statusLabel = uilabel(layout, 'Text', '', 'WordWrap', 'on');
    statusLabel.FontSize = 12;
    statusLabel.Layout.Row = 1;

    resumeButton = uibutton(layout, 'Text', 'Resume Acquisition', ...
        'Visible', 'off', 'Enable', 'off', ...
        'ButtonPushedFcn', @(src, evt)openscope_aind_signal_resume(storedFig));
    resumeButton.Layout.Row = 2;
    resumeButton.FontSize = 12;

    completeButton = uibutton(layout, 'Text', 'Signal Acquisition Complete', ...
        'Enable', 'off', 'ButtonPushedFcn', @(src, evt)openscope_aind_signal_complete(storedFig));
    completeButton.Layout.Row = 3;
    completeButton.FontSize = 12;

    storedFig.UserData = struct( ...
        'StatusLabel', statusLabel, ...
        'ResumeButton', resumeButton, ...
        'CompleteButton', completeButton);
end

fig = storedFig;
fig.Visible = 'on';
drawnow limitrate;
end


function openscope_aind_update_status(fig, message)
%OPEN_SCOPE_AIND_UPDATE_STATUS Update the status message in the UI.

if nargin < 2
    message = '';
end

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'StatusLabel') && isvalid(data.StatusLabel)
    data.StatusLabel.Text = char(message);
end
drawnow limitrate;
end


function openscope_aind_set_completion_enabled(fig, enabled)
%OPEN_SCOPE_AIND_SET_COMPLETION_ENABLED Enable/disable the completion button.

if isempty(fig) || ~isvalid(fig)
    return;
end

state = 'off';
if enabled
    state = 'on';
    assignin('base', 'OPENSCOPE_LAUNCHER_COMPLETED', false);
end

data = fig.UserData;
if isfield(data, 'CompleteButton') && isvalid(data.CompleteButton)
    data.CompleteButton.Enable = state;
    data.CompleteButton.Visible = 'on';
end
if enabled
    openscope_aind_set_resume_visible(fig, false);
end
drawnow limitrate;
end


function openscope_aind_set_resume_visible(fig, visible)
%OPEN_SCOPE_AIND_SET_RESUME_VISIBLE Toggle the resume button visibility.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'ResumeButton') && isvalid(data.ResumeButton)
    if visible
        data.ResumeButton.Visible = 'on';
        data.ResumeButton.Enable = 'on';
    else
        data.ResumeButton.Visible = 'off';
        data.ResumeButton.Enable = 'off';
    end
end

if isfield(data, 'CompleteButton') && isvalid(data.CompleteButton)
    if visible
        data.CompleteButton.Visible = 'off';
    else
        data.CompleteButton.Visible = 'on';
    end
end

drawnow limitrate;
end


function openscope_aind_signal_complete(fig)
%OPEN_SCOPE_AIND_SIGNAL_COMPLETE Notify Python that MATLAB is finished.

if isempty(fig) || ~isvalid(fig)
    return;
end

assignin('base', 'OPENSCOPE_LAUNCHER_COMPLETED', true);
openscope_aind_set_completion_enabled(fig, false);
openscope_aind_update_status(fig, 'Completion signaled. Python will continue.');

if strcmpi(fig.WaitStatus, 'waiting')
    uiresume(fig);
end
end


function openscope_aind_signal_resume(fig)
%OPEN_SCOPE_AIND_SIGNAL_RESUME Notify Python that acquisition should resume.

if isempty(fig) || ~isvalid(fig)
    return;
end

assignin('base', 'OPENSCOPE_LAUNCHER_RESUME_CONFIRMED', true);
openscope_aind_update_status(fig, 'Resume requested. Restarting acquisition...');

data = fig.UserData;
if isfield(data, 'ResumeButton') && isvalid(data.ResumeButton)
    data.ResumeButton.Enable = 'off';
end

if strcmpi(fig.WaitStatus, 'waiting')
    uiresume(fig);
end
end


function openscope_aind_close_request(fig)
%OPEN_SCOPE_AIND_CLOSE_REQUEST Handle manual closure of the UI.

if isempty(fig) || ~isvalid(fig)
    return;
end

if strcmpi(fig.WaitStatus, 'waiting')
    uiresume(fig);
end

fig.Visible = 'off';
end


function handle = openscope_aind_resolve_function(acquisitionFunction)
%OPEN_SCOPE_AIND_RESOLVE_FUNCTION Resolve a function handle or name.

if isa(acquisitionFunction, 'function_handle')
    handle = acquisitionFunction;
elseif ischar(acquisitionFunction) || isstring(acquisitionFunction)
    handle = str2func(char(acquisitionFunction));
else
    error('Acquisition function must be a function handle or name.');
end
end


function label = openscope_aind_function_label(acquisitionFunction)
%OPEN_SCOPE_AIND_FUNCTION_LABEL Return a display label for status updates.

if isa(acquisitionFunction, 'function_handle')
    label = func2str(acquisitionFunction);
elseif ischar(acquisitionFunction) || isstring(acquisitionFunction)
    label = char(acquisitionFunction);
else
    label = 'acquisition function';
end
end


function openscope_aind_prepare_for_resume(fig, acquisitionFunction)
%OPEN_SCOPE_AIND_PREPARE_FOR_RESUME Configure UI for a resume attempt.

if isempty(fig) || ~isvalid(fig)
    return;
end

openscope_aind_set_completion_enabled(fig, false);
openscope_aind_set_resume_visible(fig, true);

assignin('base', 'OPENSCOPE_LAUNCHER_RESUME_CONFIRMED', false);

label = openscope_aind_function_label(acquisitionFunction);
openscope_aind_update_status(fig, sprintf( ...
    'MATLAB engine reconnected. Press "Resume Acquisition" to continue %s.', label));

uiwait(fig);

resumeConfirmed = false;
try
    resumeConfirmed = evalin('base', 'exist(''OPENSCOPE_LAUNCHER_RESUME_CONFIRMED'', ''var'') && OPENSCOPE_LAUNCHER_RESUME_CONFIRMED');
catch
    resumeConfirmed = false;
end

if ~resumeConfirmed
    warning('OpenScope:MatlabLauncher:ResumeNotConfirmed', ...
        'Resume button was not pressed; continuing acquisition.');
end

openscope_aind_set_resume_visible(fig, false);
end


function [resumeMode, cleanedArgs] = openscope_aind_extract_resume_flag(args)
%OPEN_SCOPE_AIND_EXTRACT_RESUME_FLAG Remove and evaluate the resume flag.

resumeMode = false;
cleanedArgs = args;

idx = 1;
while idx <= numel(cleanedArgs) - 1
    key = cleanedArgs{idx};
    if ischar(key) || isstring(key)
        keyLower = lower(char(key));
        if strcmp(keyLower, 'resume')
            resumeMode = openscope_aind_to_logical(cleanedArgs{idx + 1});
            cleanedArgs(idx:idx + 1) = [];
            break;
        end
    end
    idx = idx + 1;
end
end


function tf = openscope_aind_to_logical(value)
%OPEN_SCOPE_AIND_TO_LOGICAL Convert assorted inputs to logical true/false.

if islogical(value)
    tf = value;
elseif isnumeric(value)
    tf = value ~= 0;
elseif ischar(value) || isstring(value)
    tf = any(strcmpi(char(value), {'true', '1', 'yes', 'on'}));
else
    tf = false;
end
end