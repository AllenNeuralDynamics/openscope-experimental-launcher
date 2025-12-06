function varargout = aind_launcher(varargin)
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
            varargout = aind_launcher_prepare_outputs(nargout);
            return;
        elseif firstText == "helper_register"
            varargin(1) = [];
            info = aind_launcher_helper_register(varargin{:});
            varargout = aind_launcher_prepare_outputs(nargout, info);
            return;
        elseif firstText == "helper_update_versions"
            varargin(1) = [];
            aind_launcher_helper_update_versions(varargin{:});
            varargout = aind_launcher_prepare_outputs(nargout);
            return;
        elseif firstText == "helper_set_python_start_time"
            varargin(1) = [];
            aind_launcher_helper_set_python_start_time(varargin{:});
            varargout = aind_launcher_prepare_outputs(nargout);
            return;
        elseif firstText == "helper_set_status"
            varargin(1) = [];
            aind_launcher_helper_set_status(varargin{:});
            varargout = aind_launcher_prepare_outputs(nargout);
            return;
        end
    end
end

if nargin < 1 || isempty(varargin{1})
    engineName = 'openscope_launcher';
else
    engineName = varargin{1};
end

assignin('base', 'OPENSCOPE_SESSION_FOLDER', '');
assignin('base', 'OPENSCOPE_AIND_LAUNCHER_VERSION', openscope_aind_launcher_version());

existingFig = openscope_aind_get_ui(true);
engineShared = openscope_aind_is_engine_shared(engineName);

if engineShared
    fprintf('[OpenScope] MATLAB engine already shared as ''%s''.\n', engineName);
    try
        aind_launcher_helper_register();
    catch
    end
    if ~isempty(existingFig) && isvalid(existingFig)
        openscope_aind_update_metadata(existingFig, ...
            'start', datetime('now'), ...
            'engine', engineName, ...
            'session', '');
        if strcmpi(existingFig.Visible, 'off')
            existingFig.Visible = 'on';
        end
        openscope_aind_update_status(existingFig, ...
            sprintf('Waiting for Python launcher (engine: %s)...', engineName));
        assignin('base', 'OPENSCOPE_LAUNCHER_COMPLETED', false);
        drawnow limitrate;
        return;
    end
else
    try
        matlab.engine.shareEngine(engineName);
        fprintf('[OpenScope] Shared MATLAB engine ''%s''.\n', engineName);
        try
            aind_launcher_helper_register();
        catch
        end
    catch err
        if contains(lower(err.message), 'already shared')
            fprintf('[OpenScope] MATLAB engine already shared as ''%s''.\n', engineName);
            try
                aind_launcher_helper_register();
            catch
            end
        else
            rethrow(err);
        end
    end
end

fig = openscope_aind_get_ui();
openscope_aind_update_metadata(fig, ...
    'start', datetime('now'), ...
    'engine', engineName, ...
    'session', openscope_aind_get_session_folder(), ...
    'pythonstart', []);
openscope_aind_update_status(fig, sprintf('Waiting for Python launcher (engine: %s)...', engineName));
assignin('base', 'OPENSCOPE_LAUNCHER_COMPLETED', false);
if nargout > 0
    varargout = aind_launcher_prepare_outputs(nargout);
end
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

assignin('base', 'OPENSCOPE_AIND_LAUNCHER_VERSION', openscope_aind_launcher_version());

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

openscope_aind_update_metadata(fig, 'session', sessionFolder);

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
openscope_aind_close_ui(fig);
end


function fig = openscope_aind_get_ui(existingOnly)
%OPEN_SCOPE_AIND_GET_UI Create or return the shared UI figure.

persistent storedFig

if nargin < 1
    existingOnly = false;
end

if existingOnly
    if isempty(storedFig) || ~isvalid(storedFig)
        fig = [];
    else
        fig = storedFig;
    end
    return;
end

if isempty(storedFig) || ~isvalid(storedFig)
    storedFig = uifigure('Name', 'OpenScope MATLAB Launcher', ...
        'Position', [100 100 500 240]);
    storedFig.CloseRequestFcn = @(src, evt)openscope_aind_close_request(src);

    layout = uigridlayout(storedFig, [4 1]);
    layout.RowHeight = {'1x', 'fit', 45, 45};
    layout.Padding = [12 12 12 12];
    layout.RowSpacing = 12;

    statusLabel = uilabel(layout, 'Text', '', 'WordWrap', 'on');
    statusLabel.FontSize = 12;
    statusLabel.Layout.Row = 1;

    infoLabel = uilabel(layout, 'Text', '', 'WordWrap', 'on');
    infoLabel.FontSize = 11;
    infoLabel.Layout.Row = 2;

    resumeButton = uibutton(layout, 'Text', 'Resume Acquisition', ...
        'Visible', 'off', 'Enable', 'off', ...
        'ButtonPushedFcn', @(src, evt)openscope_aind_signal_resume(storedFig));
    resumeButton.Layout.Row = 3;
    resumeButton.FontSize = 12;

    completeButton = uibutton(layout, 'Text', 'Signal Acquisition Complete', ...
        'Enable', 'off', 'ButtonPushedFcn', @(src, evt)openscope_aind_signal_complete(storedFig));
    completeButton.Layout.Row = 4;
    completeButton.FontSize = 12;

    storedFig.UserData = struct( ...
        'StatusLabel', statusLabel, ...
        'InfoLabel', infoLabel, ...
        'ResumeButton', resumeButton, ...
        'CompleteButton', completeButton, ...
        'StartTime', datetime('now'), ...
        'PythonStartTime', [], ...
        'EngineName', '', ...
        'SessionFolder', '', ...
        'LauncherVersion', '', ...
        'UpdateTimer', []);

    openscope_aind_start_timer(storedFig);
end

fig = storedFig;
fig.Visible = 'on';
drawnow limitrate;
end

function isShared = openscope_aind_is_engine_shared(engineName)
%OPEN_SCOPE_AIND_IS_ENGINE_SHARED Check if the MATLAB engine name is already shared.

isShared = false;

try
    existingNames = matlab.engine.engineName;
    if ischar(existingNames)
        existingNames = {existingNames};
    elseif isstring(existingNames)
        existingNames = cellstr(existingNames);
    end
    if iscell(existingNames)
        isShared = any(strcmp(existingNames, engineName));
    end
catch
    % If enumeration fails, assume not shared to allow shareEngine to try.
    isShared = false;
end

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
fig.UserData = data;
openscope_aind_refresh_info(fig);
drawnow limitrate;
end

function openscope_aind_update_metadata(fig, varargin)
%OPEN_SCOPE_AIND_UPDATE_METADATA Update stored metadata for info display.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
idx = 1;
while idx <= numel(varargin) - 1
    key = lower(string(varargin{idx}));
    value = varargin{idx + 1};
    switch key
        case 'start'
            if isa(value, 'datetime')
                data.StartTime = value;
            end
        case 'pythonstart'
            if isa(value, 'datetime') || isempty(value)
                data.PythonStartTime = value;
            end
        case 'engine'
            data.EngineName = char(value);
        case 'session'
            data.SessionFolder = char(value);
        case 'launcherversion'
            data.LauncherVersion = char(string(value));
    end
    idx = idx + 2;
end

fig.UserData = data;
needsTimer = true;
if isfield(data, 'UpdateTimer') && isa(data.UpdateTimer, 'timer')
    timerObj = data.UpdateTimer;
    needsTimer = isempty(timerObj) || ~isvalid(timerObj);
end

if needsTimer
    openscope_aind_start_timer(fig);
else
    openscope_aind_refresh_info(fig);
end
end

function info = aind_launcher_helper_register(varargin) %#ok<INUSD>
%AIND_LAUNCHER_HELPER_REGISTER Bridge to register helper metadata and return info.

launcherVersion = openscope_aind_launcher_version();

info = struct( ...
    'version', launcherVersion, ...
    'launcher_version', launcherVersion, ...
    'timestamp', datestr(now, 'yyyy-mm-dd HH:MM:SS')); %#ok<DATST>

assignin('base', 'OPENSCOPE_MATLAB_HELPER_INFO', info);

aind_launcher_helper_update_versions(launcherVersion);
end

function aind_launcher_helper_update_versions(launcherVersion)
%AIND_LAUNCHER_HELPER_UPDATE_VERSIONS Bridge to refresh launcher metadata in UI.

fig = openscope_aind_get_ui(true);
if isempty(fig) || ~isvalid(fig)
    return;
end

metadataArgs = {};
if nargin >= 1 && ~isempty(launcherVersion)
    metadataArgs = [metadataArgs, {'launcherversion', launcherVersion}]; %#ok<AGROW>
end

if ~isempty(metadataArgs)
    openscope_aind_update_metadata(fig, metadataArgs{:});
end
end

function aind_launcher_helper_set_python_start_time(startTime)
%AIND_LAUNCHER_HELPER_SET_PYTHON_START_TIME Bridge to update Python start timestamp.

if nargin < 1 || isempty(startTime)
    startTime = datetime('now');
elseif isnumeric(startTime)
    startTime = datetime(startTime, 'ConvertFrom', 'datenum');
elseif ischar(startTime) || isstring(startTime)
    try
        startTime = datetime(startTime);
    catch
        startTime = datetime('now');
    end
end

fig = openscope_aind_get_ui(true);
if isempty(fig) || ~isvalid(fig)
    warning('OpenScope:MatlabLauncher:NoUI', ...
        'MATLAB launcher UI not available when setting Python start time.');
    return;
end

openscope_aind_update_metadata(fig, 'pythonstart', startTime);
end

function aind_launcher_helper_set_status(message)
%AIND_LAUNCHER_HELPER_SET_STATUS Bridge to update UI status label.

if nargin < 1
    message = '';
end

fig = openscope_aind_get_ui(true);
if isempty(fig) || ~isvalid(fig)
    return;
end

openscope_aind_update_status(fig, char(string(message)));
end

function openscope_aind_start_timer(fig)
%OPEN_SCOPE_AIND_START_TIMER Ensure the periodic info timer is running.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'UpdateTimer') && isa(data.UpdateTimer, 'timer')
    timerObj = data.UpdateTimer;
    if ~isempty(timerObj) && isvalid(timerObj)
        try
            stop(timerObj);
        catch
        end
        delete(timerObj);
    end
end

timerObj = timer( ...
    'ExecutionMode', 'fixedSpacing', ...
    'Period', 1, ...
    'TimerFcn', @(~, ~)openscope_aind_timer_tick(fig), ...
    'Tag', 'OpenScopeLauncherTimer');

data.UpdateTimer = timerObj;
fig.UserData = data;

openscope_aind_refresh_info(fig);

try
    start(timerObj);
catch timerErr
    warning('OpenScope:MatlabLauncher:TimerFailed', ...
        'Failed to start UI update timer: %s', timerErr.message);
end
end

function openscope_aind_refresh_info(fig)
%OPEN_SCOPE_AIND_REFRESH_INFO Refresh informational label text.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if ~isfield(data, 'InfoLabel') || ~isvalid(data.InfoLabel)
    return;
end

if ~isfield(data, 'StartTime') || isempty(data.StartTime)
    data.StartTime = datetime('now');
end

engineName = '(unknown)';
if isfield(data, 'EngineName') && ~isempty(data.EngineName)
    engineName = data.EngineName;
end

sessionFolder = '(not set)';
if isfield(data, 'SessionFolder') && ~isempty(data.SessionFolder)
    sessionFolder = data.SessionFolder;
end

elapsedStr = openscope_aind_format_elapsed(data.StartTime);
pythonElapsedStr = '00:00:00';
pythonStartedStr = '(waiting)';
if isfield(data, 'PythonStartTime') && ~isempty(data.PythonStartTime)
    pythonElapsedStr = openscope_aind_format_elapsed(data.PythonStartTime);
    pythonStartedStr = datestr(data.PythonStartTime, 'yyyy-mm-dd HH:MM:SS');
end
startedStr = '(unknown)';
if isfield(data, 'StartTime') && ~isempty(data.StartTime)
    startedStr = datestr(data.StartTime, 'yyyy-mm-dd HH:MM:SS');
end

infoLines = {
    sprintf('Engine: %s', engineName), ...
    sprintf('Started: %s', startedStr), ...
    sprintf('Session folder: %s', sessionFolder), ...
    sprintf('GUI elapsed: %s', elapsedStr), ...
    sprintf('Python start: %s', pythonStartedStr), ...
    sprintf('Python elapsed: %s', pythonElapsedStr)
};

helperInfo = openscope_aind_fetch_helper_info();

if isfield(helperInfo, 'launcher_version') && ~isempty(helperInfo.launcher_version)
    data.LauncherVersion = char(string(helperInfo.launcher_version));
elseif isfield(helperInfo, 'version') && ~isempty(helperInfo.version)
    data.LauncherVersion = char(string(helperInfo.version));
elseif ~isfield(data, 'LauncherVersion') || isempty(data.LauncherVersion)
    data.LauncherVersion = '';
end

if isfield(data, 'LauncherVersion') && ~isempty(data.LauncherVersion)
    infoLines{end + 1} = sprintf('Launcher version: %s', data.LauncherVersion); %#ok<AGROW>
end

data.InfoLabel.Text = strjoin(infoLines, newline);
fig.UserData = data;
drawnow limitrate;
end

function openscope_aind_timer_tick(fig)
%OPEN_SCOPE_AIND_TIMER_TICK Periodic refresh for elapsed time display.

openscope_aind_refresh_info(fig);
end

function folder = openscope_aind_get_session_folder()
%OPEN_SCOPE_AIND_GET_SESSION_FOLDER Retrieve session folder from base workspace.

folder = '';
try
    existsFlag = evalin('base', 'exist(''OPENSCOPE_SESSION_FOLDER'', ''var'')');
    if existsFlag
        folderValue = evalin('base', 'OPENSCOPE_SESSION_FOLDER');
        if isstring(folderValue)
            folderValue = char(folderValue);
        elseif isnumeric(folderValue)
            folderValue = char(string(folderValue));
        end
        if ischar(folderValue)
            folder = folderValue;
        end
    end
catch
    folder = '';
end

end

function info = openscope_aind_fetch_helper_info()
%OPEN_SCOPE_AIND_FETCH_HELPER_INFO Retrieve helper metadata from base workspace.

info = struct();

try
    existsFlag = evalin('base', 'exist(''OPENSCOPE_MATLAB_HELPER_INFO'', ''var'')');
    if existsFlag
        candidate = evalin('base', 'OPENSCOPE_MATLAB_HELPER_INFO');
        if isstruct(candidate)
            info = candidate;
        end
    end
catch
    info = struct();
end
end

function openscope_aind_close_ui(fig)
%OPEN_SCOPE_AIND_CLOSE_UI Close and invalidate the OpenScope UI figure.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'UpdateTimer') && isa(data.UpdateTimer, 'timer')
    timerObj = data.UpdateTimer;
    if ~isempty(timerObj) && isvalid(timerObj)
        try
            stop(timerObj);
        catch
        end
        delete(timerObj);
    end
end

delete(fig);

end

function elapsedStr = openscope_aind_format_elapsed(startTime)
%OPEN_SCOPE_AIND_FORMAT_ELAPSED Format elapsed time as HH:MM:SS.

if nargin < 1 || isempty(startTime)
    elapsedStr = '00:00:00';
    return;
end

elapsedSeconds = round(seconds(datetime('now') - startTime));
if elapsedSeconds < 0
    elapsedSeconds = 0;
end
hours = floor(elapsedSeconds / 3600);
minutes = floor(mod(elapsedSeconds, 3600) / 60);
secondsPart = mod(elapsedSeconds, 60);
elapsedStr = sprintf('%02d:%02d:%02d', hours, minutes, secondsPart);
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

openscope_aind_close_ui(fig);
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


function outputs = aind_launcher_prepare_outputs(count, varargin)
%AIND_LAUNCHER_PREPARE_OUTPUTS Return output cell array seeded with defaults.

if nargin < 1 || count <= 0
    outputs = cell(1, 0);
    return;
end

outputs = cell(1, count);

fillCount = min(count, numel(varargin));
for idx = 1:fillCount
    outputs{idx} = varargin{idx};
end

for idx = fillCount + 1:count
    outputs{idx} = [];
end
end


function version = openscope_aind_launcher_version()
%OPEN_SCOPE_AIND_LAUNCHER_VERSION Return the MATLAB launcher UI version string.

version = '2025.12.05-1';
end


function version = openscope_aind_helper_version()
%OPEN_SCOPE_AIND_HELPER_VERSION Return the consolidated helper version string.

version = openscope_aind_launcher_version();
end