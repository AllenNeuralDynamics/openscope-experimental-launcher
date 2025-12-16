function varargout = slap2_launcher(varargin)
%SLAP2_LAUNCHER Share the current MATLAB engine for SLAP2 launchers.
%   SLAP2_LAUNCHER() registers the running MATLAB session using
%   matlab.engine.shareEngine so that the Python SLAP2 launcher can
%   attach with matlab.engine.connect_matlab.  A simple UI window is also
%   created so the experimenter can notify Python when MATLAB processing is
%   finished.

slap2_launcher_ensure_launcher_path();

if nargin >= 1
    firstArg = varargin{1};
    if ischar(firstArg) || isstring(firstArg)
        firstText = lower(string(firstArg));
        if firstText == "execute"
            varargin(1) = [];
            slap2_launcher_execute(varargin{:});
            varargout = slap2_launcher_prepare_outputs(nargout);
            return;
        elseif firstText == "helper_register"
            varargin(1) = [];
            info = slap2_launcher_helper_register(varargin{:});
            varargout = slap2_launcher_prepare_outputs(nargout, info);
            return;
        elseif firstText == "helper_update_versions"
            varargin(1) = [];
            slap2_launcher_helper_update_versions(varargin{:});
            varargout = slap2_launcher_prepare_outputs(nargout);
            return;
        elseif firstText == "helper_set_python_start_time"
            varargin(1) = [];
            slap2_launcher_helper_set_python_start_time(varargin{:});
            varargout = slap2_launcher_prepare_outputs(nargout);
            return;
        elseif firstText == "helper_set_status"
            varargin(1) = [];
            slap2_launcher_helper_set_status(varargin{:});
            varargout = slap2_launcher_prepare_outputs(nargout);
            return;
        end
    end
end

if nargin < 1 || isempty(varargin{1})
    engineName = 'slap2_launcher';
else
    engineName = varargin{1};
end

assignin('base', 'SLAP2_SESSION_FOLDER', '');
assignin('base', 'SLAP2_LAUNCHER_VERSION', slap2_launcher_version());

existingFig = slap2_launcher_get_ui(true);
engineShared = slap2_launcher_is_engine_shared(engineName);

if engineShared
    fprintf('[SLAP2] MATLAB engine already shared as ''%s''.\n', engineName);
    try
        slap2_launcher_helper_register('allow_missing_ui', true);
    catch
    end
    if ~isempty(existingFig) && isvalid(existingFig)
        slap2_launcher_update_metadata(existingFig, ...
            'start', datetime('now'), ...
            'engine', engineName, ...
            'session', '');
        if strcmpi(existingFig.Visible, 'off')
            existingFig.Visible = 'on';
        end
        slap2_launcher_update_status(existingFig, ...
            sprintf('Waiting for Python launcher (engine: %s)...', engineName));
        assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);
        drawnow limitrate;
        return;
    end
else
    try
        matlab.engine.shareEngine(engineName);
        fprintf('[SLAP2] Shared MATLAB engine ''%s''.\n', engineName);
        try
            slap2_launcher_helper_register('allow_missing_ui', true);
        catch
        end
    catch err
        messageLower = lower(err.message);
        if contains(messageLower, 'already shared') || contains(messageLower, 'shared already')
            sharedNames = slap2_launcher_get_shared_engine_names();
            if any(strcmp(sharedNames, engineName))
                fprintf('[SLAP2] MATLAB engine already shared as ''%s''.\n', engineName);
                try
                    slap2_launcher_helper_register('allow_missing_ui', true);
                catch
                end
            else
                if isempty(sharedNames)
                    sharedNames = {'(unknown)'};
                end
                formattedNames = strjoin(sharedNames, ''', ''');
                error('SLAP2:MatlabLauncher:SharedEngineNameMismatch', ...
                    ['A MATLAB engine is already shared using name(s) ''%s''. ' ...
                     'Close the existing shared session or share MATLAB as ''%s'' and retry.'], ...
                    formattedNames, engineName);
            end
        else
            rethrow(err);
        end
    end
end

fig = slap2_launcher_get_ui();
slap2_launcher_update_metadata(fig, ...
    'start', datetime('now'), ...
    'engine', engineName, ...
    'session', slap2_launcher_get_session_folder(), ...
    'pythonstart', []);
slap2_launcher_update_status(fig, sprintf('Waiting for Python launcher (engine: %s)...', engineName));
assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);
slap2_launcher_set_pending_stage('start');
if nargout > 0
    varargout = slap2_launcher_prepare_outputs(nargout);
end
end


function slap2_launcher_execute(varargin)
%SLAP2_LAUNCHER_EXECUTE Run the SLAP2 acquisition entry point.
%   Invoked from Python after the engine connection is established. Holds
%   at the UI start/stop prompts so the user can gate the acquisition.

assignin('base', 'SLAP2_LAUNCHER_VERSION', slap2_launcher_version());

fig = slap2_launcher_get_ui();
slap2_launcher_set_python_control(fig, true);

[resumeMode, varargin] = slap2_launcher_extract_resume_flag(varargin);
[resumeStage, varargin] = slap2_launcher_extract_resume_stage(varargin);
[rigDescriptionPath, varargin] = slap2_launcher_extract_named_arg(varargin, 'rig_description_path');

if ~isempty(rigDescriptionPath)
    slap2_launcher_set_rig_path(fig, rigDescriptionPath);
end

sessionFolder = '';
if ~isempty(varargin)
    firstArg = varargin{1};
    if ischar(firstArg) || isstring(firstArg)
        candidate = char(firstArg);
        if isfolder(candidate)
            sessionFolder = candidate;
            varargin(1) = [];
        end
    end
end

slap2_launcher_update_metadata(fig, 'session', sessionFolder);
if ~isempty(sessionFolder)
    assignin('base', 'SLAP2_SESSION_FOLDER', sessionFolder);
end

originalDir = pwd;
restoreDir = onCleanup(@() cd(originalDir)); %#ok<NASGU>

slap2_launcher_prepare_start_controls(fig, resumeMode);

if resumeMode
    if strcmpi(resumeStage, 'completion')
        resumeStatus = [
            'MATLAB reconnected after a crash. Press "Resume SLAP2 acquisition" ', ...
            'to relaunch slap2, then press "End SLAP2 acquisition" when complete.'
        ];
    else
        resumeStatus = 'MATLAB reconnected. Press "Resume SLAP2 acquisition" to continue.';
    end
    slap2_launcher_update_status(fig, resumeStatus);
end

slap2_launcher_wait_for_flag(fig, 'SLAP2_LAUNCHER_START_CONFIRMED', ...
    'SLAP2:MatlabLauncher:StartNotConfirmed', ...
    'Start SLAP2 acquisition was not confirmed before continuing.');

sessionFolder = slap2_launcher_current_session_folder(fig);
if ~isempty(sessionFolder)
    assignin('base', 'SLAP2_SESSION_FOLDER', sessionFolder);
    try
        cd(sessionFolder);
    catch dirErr
        warning('SLAP2:MatlabLauncher:ChangeDirFailed', ...
            'Failed to change directory to session folder "%s": %s', sessionFolder, dirErr.message);
    end
end

slap2_launcher_set_python_control(fig, false);
slap2_launcher_update_status(fig, 'Running slap2 ...');

try
    slap2(varargin{:});
catch err
    slap2_launcher_update_status(fig, ['Error: ' err.message]);
    slap2_launcher_reset_start_controls(fig, resumeMode);
    rethrow(err);
end

slap2_launcher_update_status(fig, 'Acquisition complete. Press "End SLAP2 acquisition" when ready to continue.');
slap2_launcher_prepare_for_completion(fig);

slap2_launcher_wait_for_flag(fig, 'SLAP2_LAUNCHER_COMPLETED', ...
    'SLAP2:MatlabLauncher:CompletionNotConfirmed', ...
    'End SLAP2 acquisition was not confirmed before continuing.');

slap2_launcher_set_python_control(fig, false);
slap2_launcher_close_ui(fig);
end

function fig = slap2_launcher_get_ui(existingOnly)
%SLAP2_LAUNCHER_GET_UI Create or return the shared UI figure.

persistent storedFig

if nargin < 1
    existingOnly = false;
end

if isempty(storedFig) || ~isvalid(storedFig)
    % Attempt to recover an existing launcher window if the persistent handle was lost.
    recovered = findall(0, 'Type', 'figure', 'Tag', 'SLAP2LauncherUI');
    if isempty(recovered)
        recovered = findall(0, 'Type', 'figure', 'Name', 'SLAP2 MATLAB Launcher');
    end
    if ~isempty(recovered)
        storedFig = recovered(1);
    end
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
    storedFig = uifigure('Name', 'SLAP2 MATLAB Launcher', ...
        'Position', [100 100 500 320]);
    storedFig.Tag = 'SLAP2LauncherUI';
    storedFig.CloseRequestFcn = @(src, evt)slap2_launcher_close_request(src);

    layout = uigridlayout(storedFig, [5 1]);
    layout.RowHeight = {'fit', 'fit', 'fit', '1x', 45};
    layout.Padding = [10 10 10 10];
    layout.RowSpacing = 8;

    statusLabel = uilabel(layout, 'Text', '', 'WordWrap', 'on');
    statusLabel.FontSize = 12;
    statusLabel.Layout.Row = 1;

    rigRow = uigridlayout(layout, [1 2]);
    rigRow.ColumnWidth = {'1x', 'fit'};
    rigRow.ColumnSpacing = 8;
    rigRow.Padding = [0 0 0 0];

    rigLabel = uilabel(rigRow, 'Text', 'Rig description: (not selected)', 'WordWrap', 'on');
    rigLabel.FontSize = 11;
    rigLabel.Layout.Column = 1;

    rigButton = uibutton(rigRow, 'Text', 'Select Rig Description', ...
        'ButtonPushedFcn', @(src, evt)slap2_launcher_select_rig_description(storedFig));
    rigButton.Layout.Column = 2;

    sessionRow = uigridlayout(layout, [1 2]);
    sessionRow.Layout.Row = 3;
    sessionRow.ColumnWidth = {'1x', 'fit'};
    sessionRow.ColumnSpacing = 8;
    sessionRow.Padding = [0 0 0 0];

    sessionLabel = uilabel(sessionRow, 'Text', 'Session folder: (not selected)', 'WordWrap', 'on');
    sessionLabel.FontSize = 11;
    sessionLabel.Layout.Column = 1;

    sessionButton = uibutton(sessionRow, 'Text', 'Select Rig Session Folder', ...
        'ButtonPushedFcn', @(src, evt)slap2_launcher_select_session_folder(storedFig));
    sessionButton.Layout.Column = 2;

    infoLabel = uilabel(layout, 'Text', '', 'WordWrap', 'on');
    infoLabel.FontSize = 11;
    infoLabel.Layout.Row = 4;

    startStopButton = uibutton(layout, 'Text', 'Start SLAP2 acquisition', ...
        'Enable', 'off', 'ButtonPushedFcn', @(src, evt)slap2_launcher_start_stop_pressed(storedFig));
    startStopButton.Layout.Row = 5;
    startStopButton.FontSize = 13;

    storedFig.UserData = struct( ...
        'StatusLabel', statusLabel, ...
        'InfoLabel', infoLabel, ...
        'RigLabel', rigLabel, ...
        'RigSelectButton', rigButton, ...
        'SessionLabel', sessionLabel, ...
        'SessionSelectButton', sessionButton, ...
        'StartStopButton', startStopButton, ...
        'StartTime', datetime('now'), ...
        'PythonStartTime', [], ...
        'EngineName', '', ...
        'SessionFolder', '', ...
        'LauncherVersion', '', ...
        'RigPath', '', ...
        'RigCopyCompleted', false, ...
        'RigCopyTarget', '', ...
        'ResumeMode', false, ...
        'StartStopState', 'start', ...
        'ControlledByPython', false, ...
        'ManualCompletionPending', false, ...
        'UpdateTimer', []);

    slap2_launcher_start_timer(storedFig);

    defaultRigPath = slap2_launcher_default_rig_path();
    if ~isempty(defaultRigPath)
        slap2_launcher_set_rig_path(storedFig, defaultRigPath);
    else
        slap2_launcher_refresh_rig_display(storedFig);
    end

    slap2_launcher_prepare_manual_controls(storedFig);
end

fig = storedFig;
fig.Visible = 'on';
drawnow limitrate;
end

function isShared = slap2_launcher_is_engine_shared(engineName)
%SLAP2_LAUNCHER_IS_ENGINE_SHARED Check if the MATLAB engine name is already shared.

isShared = false;

try
    existingNames = slap2_launcher_get_shared_engine_names();
    if ~isempty(existingNames)
        isShared = any(strcmp(existingNames, engineName));
    end
catch
    % If enumeration fails, assume not shared to allow shareEngine to try.
    isShared = false;
end

end

function names = slap2_launcher_get_shared_engine_names()
%SLAP2_LAUNCHER_GET_SHARED_ENGINE_NAMES Return currently shared engine names.

names = {};
try
    existingNames = matlab.engine.engineName;
    if ischar(existingNames)
        names = {existingNames};
    elseif isstring(existingNames)
        names = cellstr(existingNames);
    elseif iscell(existingNames)
        names = existingNames;
    end
catch
    names = {};
end

end

function slap2_launcher_update_status(fig, message)
%SLAP2_LAUNCHER_UPDATE_STATUS Update the status message in the UI.

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
slap2_launcher_refresh_info(fig);
drawnow limitrate;
end

function slap2_launcher_update_metadata(fig, varargin)
%SLAP2_LAUNCHER_UPDATE_METADATA Update stored metadata for info display.

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
            data.RigCopyCompleted = false;
            data.RigCopyTarget = '';
            assignin('base', 'SLAP2_RIG_DESCRIPTION_TARGET', '');
            assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);
            try
                helperInfo = evalin('base', 'SLAP2_MATLAB_HELPER_INFO');
                if isstruct(helperInfo)
                    helperInfo.rig_description_target = '';
                    assignin('base', 'SLAP2_MATLAB_HELPER_INFO', helperInfo);
                end
            catch
            end
        case 'launcherversion'
            data.LauncherVersion = char(string(value));
    end
    idx = idx + 2;
end

fig.UserData = data;
slap2_launcher_refresh_session_display(fig);
needsTimer = true;
if isfield(data, 'UpdateTimer') && isa(data.UpdateTimer, 'timer')
    timerObj = data.UpdateTimer;
    needsTimer = isempty(timerObj) || ~isvalid(timerObj);
end

if needsTimer
    slap2_launcher_start_timer(fig);
else
    slap2_launcher_refresh_info(fig);
end

slap2_launcher_handle_rig_copy(fig);
slap2_launcher_update_start_ready_state(fig);
slap2_launcher_sync_manual_start_state(fig);
end

function slap2_launcher_select_rig_description(fig)
%SLAP2_LAUNCHER_SELECT_RIG_DESCRIPTION Prompt user to choose rig JSON file.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;

initialDir = slap2_launcher_default_rig_root();
if isfield(data, 'RigPath') && ~isempty(data.RigPath)
    candidate = char(data.RigPath);
    if exist(candidate, 'file')
        initialDir = fileparts(candidate);
    elseif exist(fileparts(candidate), 'dir')
        initialDir = fileparts(candidate);
    end
end

[fileName, filePath] = uigetfile({'*.json', 'JSON files (*.json)'; '*.*', 'All files'}, ...
    'Select Rig description', initialDir);

if isequal(fileName, 0)
    return;
end

rigPath = fullfile(filePath, fileName);
slap2_launcher_set_rig_path(fig, rigPath);
end

function slap2_launcher_set_rig_path(fig, rigPath)
%SLAP2_LAUNCHER_SET_RIG_PATH Update stored rig path and refresh UI/copy state.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
data.RigPath = slap2_launcher_to_text(rigPath);
data.RigCopyCompleted = false;
data.RigCopyTarget = '';
fig.UserData = data;

assignin('base', 'SLAP2_RIG_DESCRIPTION_SOURCE', data.RigPath);

try
    helperInfo = evalin('base', 'SLAP2_MATLAB_HELPER_INFO');
    if isstruct(helperInfo)
        helperInfo.rig_description_path = data.RigPath;
        helperInfo.rig_description_target = '';
        assignin('base', 'SLAP2_MATLAB_HELPER_INFO', helperInfo);
    end
catch
    % helper info may not exist yet; safe to ignore
end

slap2_launcher_refresh_rig_display(fig);
slap2_launcher_handle_rig_copy(fig);
slap2_launcher_update_start_ready_state(fig);
slap2_launcher_sync_manual_start_state(fig);
end

function slap2_launcher_refresh_rig_display(fig)
%SLAP2_LAUNCHER_REFRESH_RIG_DISPLAY Refresh rig label text.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;

if ~isfield(data, 'RigLabel') || ~isvalid(data.RigLabel)
    return;
end

labelText = 'Rig description: (not selected)';
if isfield(data, 'RigPath') && ~isempty(data.RigPath)
    candidate = char(data.RigPath);
    if exist(candidate, 'file')
        labelText = sprintf('Rig description: %s', candidate);
    else
        labelText = sprintf('Rig description: %s (missing)', candidate);
    end
end

data.RigLabel.Text = labelText;
fig.UserData = data;
drawnow limitrate;
end

function slap2_launcher_refresh_session_display(fig)
%SLAP2_LAUNCHER_REFRESH_SESSION_DISPLAY Refresh session folder label text.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;

if ~isfield(data, 'SessionLabel') || ~isvalid(data.SessionLabel)
    return;
end

labelText = 'Session folder: (not selected)';
if isfield(data, 'SessionFolder') && ~isempty(data.SessionFolder)
    candidate = char(data.SessionFolder);
    if isfolder(candidate)
        labelText = sprintf('Session folder: %s', candidate);
    else
        labelText = sprintf('Session folder: %s (missing)', candidate);
    end
end

data.SessionLabel.Text = labelText;
fig.UserData = data;
drawnow limitrate;
end

function slap2_launcher_select_session_folder(fig)
%SLAP2_LAUNCHER_SELECT_SESSION_FOLDER Allow operator to pick a session folder.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
initialDir = '';
if isfield(data, 'SessionFolder') && ~isempty(data.SessionFolder) && isfolder(data.SessionFolder)
    initialDir = char(data.SessionFolder);
end

selectedFolder = uigetdir(initialDir, 'Select rig session folder');
if isequal(selectedFolder, 0)
    return;
end

slap2_launcher_apply_session_folder(fig, char(selectedFolder));
end

function slap2_launcher_apply_session_folder(fig, sessionFolder)
%SLAP2_LAUNCHER_APPLY_SESSION_FOLDER Persist and display a session folder.

if isempty(fig) || ~isvalid(fig)
    return;
end

if nargin < 2 || isempty(sessionFolder)
    return;
end

slap2_launcher_update_metadata(fig, 'session', sessionFolder);
assignin('base', 'SLAP2_SESSION_FOLDER', sessionFolder);
assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);
slap2_launcher_refresh_session_display(fig);
slap2_launcher_refresh_info(fig);
slap2_launcher_update_start_ready_state(fig);
end

function slap2_launcher_prepare_start_controls(fig, resumeMode)
%SLAP2_LAUNCHER_PREPARE_START_CONTROLS Enable the start portion of the toggle button.

if isempty(fig) || ~isvalid(fig)
    return;
end

if nargin < 2
    resumeMode = false;
end

data = fig.UserData;
data.ResumeMode = logical(resumeMode);
data.StartStopState = 'start';

startText = 'Start SLAP2 acquisition';
if data.ResumeMode
    startText = 'Resume SLAP2 acquisition';
end

if isfield(data, 'StartStopButton') && isvalid(data.StartStopButton)
    data.StartStopButton.Text = startText;
end

fig.UserData = data;
assignin('base', 'SLAP2_LAUNCHER_START_CONFIRMED', false);
assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);
slap2_launcher_set_pending_stage('start');
slap2_launcher_update_start_ready_state(fig, sprintf('Press "%s" to launch the acquisition.', startText));
end

function slap2_launcher_reset_start_controls(fig, resumeMode)
%SLAP2_LAUNCHER_RESET_START_CONTROLS Revert to the start state after an error.

slap2_launcher_prepare_start_controls(fig, resumeMode);
end

function slap2_launcher_start_stop_pressed(fig)
%SLAP2_LAUNCHER_START_STOP_PRESSED Handle start/stop button presses.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
state = 'idle';
if isfield(data, 'StartStopState') && ~isempty(data.StartStopState)
    state = char(string(data.StartStopState));
end

switch state
    case {'start', 'idle'}
        if ~slap2_launcher_has_session_folder(fig)
            slap2_launcher_update_status(fig, 'Select a session folder before starting SLAP2.');
            return;
        end
        if ~slap2_launcher_has_rig_selection(fig, true)
            slap2_launcher_update_status(fig, 'Select a rig description before starting SLAP2.');
            return;
        end
        if slap2_launcher_is_python_controlled(fig) && strcmpi(state, 'start')
            slap2_launcher_signal_start(fig);
        elseif slap2_launcher_is_python_controlled(fig)
            slap2_launcher_update_status(fig, 'Waiting for Python to request start.');
        else
            slap2_launcher_run_manual_acquisition(fig);
        end
    case 'stop'
        slap2_launcher_signal_complete(fig);
    otherwise
        % Ignore presses while running or after completion.
end
end


function slap2_launcher_run_manual_acquisition(fig)
%SLAP2_LAUNCHER_RUN_MANUAL_ACQUISITION Execute SLAP2 directly from MATLAB.

if isempty(fig) || ~isvalid(fig)
    return;
end

sessionFolder = slap2_launcher_current_session_folder(fig);
rigPath = slap2_launcher_current_rig_path(fig);

slap2_launcher_prepare_manual_run_state(fig);
slap2_launcher_set_manual_completion_pending(fig, false);

if ~isempty(rigPath)
    slap2_launcher_set_rig_path(fig, rigPath);
end

if ~isempty(sessionFolder)
    assignin('base', 'SLAP2_SESSION_FOLDER', sessionFolder);
end

originalDir = pwd;
restoreDir = onCleanup(@() cd(originalDir)); %#ok<NASGU>

if ~isempty(sessionFolder)
    try
        cd(sessionFolder);
    catch dirErr
        warning('SLAP2:MatlabLauncher:ChangeDirFailed', ...
            'Failed to change directory to session folder "%s": %s', sessionFolder, dirErr.message);
    end
end

slap2_launcher_update_status(fig, 'Running slap2 ...');

try
    slap2();
catch err
    slap2_launcher_update_status(fig, ['Error: ' err.message]);
    slap2_launcher_reset_manual_run_state(fig);
    rethrow(err);
end

slap2_launcher_update_status(fig, 'Acquisition complete. Press "End SLAP2 acquisition" when ready to continue.');
slap2_launcher_prepare_for_completion(fig);
slap2_launcher_set_manual_completion_pending(fig, true);
end


function slap2_launcher_prepare_manual_controls(fig)
%SLAP2_LAUNCHER_PREPARE_MANUAL_CONTROLS Configure start button for manual mode.

if isempty(fig) || ~isvalid(fig)
    return;
end

if slap2_launcher_is_python_controlled(fig)
    return;
end

data = fig.UserData;
data.StartStopState = 'start';
if isfield(data, 'StartStopButton') && isvalid(data.StartStopButton)
    data.StartStopButton.Text = 'Start SLAP2 acquisition';
    data.StartStopButton.Enable = 'off';
end
fig.UserData = data;

assignin('base', 'SLAP2_LAUNCHER_START_CONFIRMED', false);
assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);

slap2_launcher_update_start_ready_state(fig, ...
    'Select a session folder and rig description before starting SLAP2.');
slap2_launcher_sync_manual_start_state(fig);
slap2_launcher_restore_pending_stage(fig);
end

function slap2_launcher_signal_start(fig)
%SLAP2_LAUNCHER_SIGNAL_START Notify the launcher that the operator pressed start.

if isempty(fig) || ~isvalid(fig)
    return;
end

assignin('base', 'SLAP2_LAUNCHER_START_CONFIRMED', true);
assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);

data = fig.UserData;
data.StartStopState = 'running';
if isfield(data, 'StartStopButton') && isvalid(data.StartStopButton)
    data.StartStopButton.Text = 'SLAP2 acquisition running...';
    data.StartStopButton.Enable = 'off';
end
fig.UserData = data;

if strcmpi(fig.WaitStatus, 'waiting')
    uiresume(fig);
end
end

function slap2_launcher_prepare_for_completion(fig)
%SLAP2_LAUNCHER_PREPARE_FOR_COMPLETION Configure button for the end state.

if isempty(fig) || ~isvalid(fig)
    return;
end

assignin('base', 'SLAP2_LAUNCHER_COMPLETED', false);

data = fig.UserData;
data.StartStopState = 'stop';
if isfield(data, 'StartStopButton') && isvalid(data.StartStopButton)
    data.StartStopButton.Text = 'End SLAP2 acquisition';
    data.StartStopButton.Enable = 'on';
end
fig.UserData = data;
end


function slap2_launcher_set_python_control(fig, tf)
%SLAP2_LAUNCHER_SET_PYTHON_CONTROL Track whether Python owns the UI state.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
data.ControlledByPython = logical(tf);
fig.UserData = data;
end


function slap2_launcher_prepare_manual_run_state(fig)
%SLAP2_LAUNCHER_PREPARE_MANUAL_RUN_STATE Update UI state for manual execution.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
data.StartStopState = 'running';
if isfield(data, 'StartStopButton') && isvalid(data.StartStopButton)
    data.StartStopButton.Text = 'SLAP2 acquisition running...';
    data.StartStopButton.Enable = 'off';
end
fig.UserData = data;
drawnow limitrate;
end


function slap2_launcher_reset_manual_run_state(fig)
%SLAP2_LAUNCHER_RESET_MANUAL_RUN_STATE Restore start-ready state in manual mode.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
data.StartStopState = 'start';
if isfield(data, 'StartStopButton') && isvalid(data.StartStopButton)
    data.StartStopButton.Text = 'Start SLAP2 acquisition';
    data.StartStopButton.Enable = 'off';
end
fig.UserData = data;

slap2_launcher_update_start_ready_state(fig);
end


function slap2_launcher_set_manual_completion_pending(fig, tf)
%SLAP2_LAUNCHER_SET_MANUAL_COMPLETION_PENDING Track manual completion prompts.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
data.ManualCompletionPending = logical(tf);
fig.UserData = data;
end


function tf = slap2_launcher_manual_completion_pending(fig)
%SLAP2_LAUNCHER_MANUAL_COMPLETION_PENDING Return manual completion flag.

tf = false;
if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'ManualCompletionPending') && ~isempty(data.ManualCompletionPending)
    tf = logical(data.ManualCompletionPending);
end
end


function slap2_launcher_sync_manual_start_state(fig)
%SLAP2_LAUNCHER_SYNC_MANUAL_START_STATE Ensure start button usable headless.

if isempty(fig) || ~isvalid(fig)
    return;
end

if slap2_launcher_is_python_controlled(fig)
    return;
end

data = fig.UserData;
if ~isfield(data, 'StartStopState') || strcmpi(data.StartStopState, 'idle')
    data.StartStopState = 'start';
    fig.UserData = data;
end

slap2_launcher_update_start_ready_state(fig);
end


function slap2_launcher_restore_pending_stage(fig)
%SLAP2_LAUNCHER_RESTORE_PENDING_STAGE Reapply pending completion prompts.

if isempty(fig) || ~isvalid(fig)
    return;
end

stage = slap2_launcher_get_pending_stage();
if strcmpi(stage, 'completion')
    slap2_launcher_prepare_for_completion(fig);
    if ~slap2_launcher_is_python_controlled(fig)
        slap2_launcher_update_status(fig, ...
            'Python launcher needs confirmation. Press "End SLAP2 acquisition" to resume.');
    end
end
end


function slap2_launcher_wait_for_flag(fig, flagName, errorId, errorMessage)
%SLAP2_LAUNCHER_WAIT_FOR_FLAG Block until the specified launcher flag is true.

while true
    slap2_launcher_assert_ui_available(fig, flagName);

    uiwait(fig);

    if slap2_launcher_get_flag(flagName)
        return;
    end

    if isempty(fig) || ~isvalid(fig)
        slap2_launcher_raise_ui_unavailable(flagName);
    end

    error(errorId, errorMessage);
end
end


function slap2_launcher_assert_ui_available(fig, flagName)
%SLAP2_LAUNCHER_ASSERT_UI_AVAILABLE Throw if the launcher UI was destroyed.

if isempty(fig) || ~isvalid(fig)
    slap2_launcher_raise_ui_unavailable(flagName);
end
end


function slap2_launcher_raise_ui_unavailable(flagName)
%SLAP2_LAUNCHER_RAISE_UI_UNAVAILABLE Signal that the UI closed unexpectedly.

if nargin < 1 || isempty(flagName)
    flagName = 'launcher state';
end

error('SLAP2:MatlabLauncher:UIUnavailable', ...
    ['The SLAP2 launcher UI was closed while waiting for "' char(flagName) '" confirmation. ' ...
     'Restart MATLAB, run slap2_launcher again, and allow Python to resume.']);
end

function flagValue = slap2_launcher_get_flag(flagName)
%SLAP2_LAUNCHER_GET_FLAG Read a logical flag from the base workspace.

flagValue = false;
try
    flagValue = evalin('base', sprintf('exist(''%s'', ''var'') && logical(%s)', flagName, flagName)); %#ok<EVLR>
catch
    flagValue = false;
end
end

function folder = slap2_launcher_current_session_folder(fig)
%SLAP2_LAUNCHER_CURRENT_SESSION_FOLDER Return the active session folder string.

folder = '';
if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'SessionFolder') && ~isempty(data.SessionFolder)
    folder = char(data.SessionFolder);
end
end

function path = slap2_launcher_current_rig_path(fig)
%SLAP2_LAUNCHER_CURRENT_RIG_PATH Return the selected rig description path.

path = '';
if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'RigPath') && ~isempty(data.RigPath)
    path = char(data.RigPath);
end
end

function tf = slap2_launcher_has_session_folder(fig)
%SLAP2_LAUNCHER_HAS_SESSION_FOLDER Determine if a session folder is selected.

tf = ~isempty(slap2_launcher_current_session_folder(fig));
end


function tf = slap2_launcher_has_rig_selection(fig, requireExistingFile)
%SLAP2_LAUNCHER_HAS_RIG_SELECTION Determine if a rig description is selected.

if nargin < 2
    requireExistingFile = false;
end

tf = false;
if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if ~isfield(data, 'RigPath') || isempty(data.RigPath)
    return;
end

candidate = slap2_launcher_to_text(data.RigPath);
if isempty(candidate)
    return;
end

if requireExistingFile
    tf = exist(candidate, 'file') == 2;
else
    tf = true;
end
end


function ready = slap2_launcher_ready_to_start(fig)
%SLAP2_LAUNCHER_READY_TO_START Confirm both rig and session are configured.

ready = slap2_launcher_has_session_folder(fig) && slap2_launcher_has_rig_selection(fig, true);
end


function tf = slap2_launcher_is_python_controlled(fig)
%SLAP2_LAUNCHER_IS_PYTHON_CONTROLLED Determine if Python owns the UI state.

tf = false;
if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if isfield(data, 'ControlledByPython') && ~isempty(data.ControlledByPython)
    tf = logical(data.ControlledByPython);
end
end


function ready = slap2_launcher_update_start_ready_state(fig, statusMessage)
%SLAP2_LAUNCHER_UPDATE_START_READY_STATE Toggle start button availability.

ready = false;
if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;
if ~isfield(data, 'StartStopButton') || ~isvalid(data.StartStopButton)
    return;
end

state = 'idle';
if isfield(data, 'StartStopState') && ~isempty(data.StartStopState)
    state = char(string(data.StartStopState));
end

if strcmpi(state, 'idle')
    data.StartStopButton.Enable = 'off';
    fig.UserData = data;
    return;
end

if ~strcmpi(state, 'start')
    return;
end

ready = slap2_launcher_ready_to_start(fig);
if ready
    data.StartStopButton.Enable = 'on';
else
    data.StartStopButton.Enable = 'off';
end

fig.UserData = data;

if nargin >= 2 && ~isempty(statusMessage)
    if ~ready
        statusMessage = 'Select a session folder and rig description before starting SLAP2.';
    end
    slap2_launcher_update_status(fig, statusMessage);
end
end

function slap2_launcher_handle_rig_copy(fig)
%SLAP2_LAUNCHER_HANDLE_RIG_COPY Copy rig description into session folder if needed.

if isempty(fig) || ~isvalid(fig)
    return;
end

data = fig.UserData;

if ~isfield(data, 'SessionFolder') || isempty(data.SessionFolder)
    return;
end

sessionFolder = char(data.SessionFolder);
if ~exist(sessionFolder, 'dir')
    return;
end

if ~isfield(data, 'RigPath') || isempty(data.RigPath)
    return;
end

rigPath = char(data.RigPath);
if ~exist(rigPath, 'file')
    return;
end

destPath = fullfile(sessionFolder, 'rigDescription.json');

if isfield(data, 'RigCopyCompleted') && data.RigCopyCompleted
    if isfield(data, 'RigCopyTarget') && ~isempty(data.RigCopyTarget) && strcmpi(data.RigCopyTarget, destPath)
        if exist(destPath, 'file')
            return;
        end
    end
end

try
    copyfile(rigPath, destPath, 'f');
    data.RigCopyCompleted = true;
    data.RigCopyTarget = destPath;
    assignin('base', 'SLAP2_RIG_DESCRIPTION_TARGET', destPath);
catch err
    warning('SLAP2:MatlabLauncher:RigCopyFailed', ...
        'Failed to copy rig description to session folder: %s', err.message);
    data.RigCopyCompleted = false;
    data.RigCopyTarget = '';
    assignin('base', 'SLAP2_RIG_DESCRIPTION_TARGET', '');
end

fig.UserData = data;
slap2_launcher_refresh_info(fig);

try
    helperInfo = evalin('base', 'SLAP2_MATLAB_HELPER_INFO');
    if isstruct(helperInfo)
        helperInfo.rig_description_path = data.RigPath;
        helperInfo.rig_description_target = data.RigCopyTarget;
        assignin('base', 'SLAP2_MATLAB_HELPER_INFO', helperInfo);
    end
catch
    % ignore if helper info not yet initialized
end
end

function root = slap2_launcher_default_rig_root()
%SLAP2_LAUNCHER_DEFAULT_RIG_ROOT Folder to search for rig description.

root = 'F:\slap2Data';
end

function path = slap2_launcher_default_rig_path()
%SLAP2_LAUNCHER_DEFAULT_RIG_PATH Default rig description file if available.

candidate = fullfile(slap2_launcher_default_rig_root(), 'currentRigDescription.json');
if exist(candidate, 'file')
    path = candidate;
else
    path = '';
end
end

function info = slap2_launcher_helper_register(varargin)
%SLAP2_LAUNCHER_HELPER_REGISTER Bridge to register helper metadata and return info.

allowMissingUi = false;
idx = 1;
while idx <= numel(varargin)
    key = lower(string(varargin{idx}));
    if key == "allow_missing_ui"
        if idx < numel(varargin)
            allowMissingUi = slap2_launcher_to_logical(varargin{idx + 1});
            idx = idx + 2;
        else
            allowMissingUi = true;
            idx = idx + 1;
        end
    else
        idx = idx + 1;
    end
end

launcherVersion = slap2_launcher_version();

info = struct( ...
    'version', launcherVersion, ...
    'launcher_version', launcherVersion, ...
    'timestamp', datestr(now, 'yyyy-mm-dd HH:MM:SS'), ...
    'rig_description_path', '', ...
    'rig_description_target', ''); %#ok<DATST>

assignin('base', 'SLAP2_MATLAB_HELPER_INFO', info);

fig = slap2_launcher_get_ui(true);
if isempty(fig) || ~isvalid(fig)
    if allowMissingUi
        return;
    end
    error('SLAP2:MatlabLauncher:UIUnavailable', ...
        ['The SLAP2 MATLAB launcher UI is not running. Launch MATLAB, ' ...
         'execute slap2_launcher, and share the engine before starting the Python launcher.']);
end

data = fig.UserData;
if isstruct(data)
    if isfield(data, 'RigPath') && ~isempty(data.RigPath)
        info.rig_description_path = char(data.RigPath);
    end
    if isfield(data, 'RigCopyTarget') && ~isempty(data.RigCopyTarget)
        info.rig_description_target = char(data.RigCopyTarget);
    end
end

assignin('base', 'SLAP2_MATLAB_HELPER_INFO', info);

slap2_launcher_helper_update_versions(launcherVersion);
end

function slap2_launcher_helper_update_versions(launcherVersion)
%SLAP2_LAUNCHER_HELPER_UPDATE_VERSIONS Bridge to refresh launcher metadata in UI.

fig = slap2_launcher_get_ui(true);
if isempty(fig) || ~isvalid(fig)
    return;
end

metadataArgs = {};
if nargin >= 1 && ~isempty(launcherVersion)
    metadataArgs = [metadataArgs, {'launcherversion', launcherVersion}]; %#ok<AGROW>
end

if ~isempty(metadataArgs)
    slap2_launcher_update_metadata(fig, metadataArgs{:});
end
end

function slap2_launcher_helper_set_python_start_time(startTime)
%SLAP2_LAUNCHER_HELPER_SET_PYTHON_START_TIME Bridge to update Python start timestamp.

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

fig = slap2_launcher_get_ui(true);
if isempty(fig) || ~isvalid(fig)
    warning('SLAP2:MatlabLauncher:NoUI', ...
        'MATLAB launcher UI not available when setting Python start time.');
    return;
end

slap2_launcher_update_metadata(fig, 'pythonstart', startTime);
end

function slap2_launcher_helper_set_status(message)
%SLAP2_LAUNCHER_HELPER_SET_STATUS Bridge to update UI status label.

if nargin < 1
    message = '';
end

fig = slap2_launcher_get_ui(true);
if isempty(fig) || ~isvalid(fig)
    return;
end

slap2_launcher_update_status(fig, char(string(message)));
end

function slap2_launcher_start_timer(fig)
%SLAP2_LAUNCHER_START_TIMER Ensure the periodic info timer is running.

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
    'TimerFcn', @(~, ~)slap2_launcher_timer_tick(fig), ...
    'Tag', 'SLAP2LauncherTimer');

data.UpdateTimer = timerObj;
fig.UserData = data;

slap2_launcher_refresh_info(fig);

try
    start(timerObj);
catch timerErr
    warning('SLAP2:MatlabLauncher:TimerFailed', ...
        'Failed to start UI update timer: %s', timerErr.message);
end
end

function slap2_launcher_refresh_info(fig)
%SLAP2_LAUNCHER_REFRESH_INFO Refresh informational label text.

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

elapsedStr = slap2_launcher_format_elapsed(data.StartTime);
pythonElapsedStr = '00:00:00';
pythonStartedStr = '(waiting)';
if isfield(data, 'PythonStartTime') && ~isempty(data.PythonStartTime)
    pythonElapsedStr = slap2_launcher_format_elapsed(data.PythonStartTime);
    pythonStartedStr = datestr(data.PythonStartTime, 'yyyy-mm-dd HH:MM:SS');
end
startedStr = '(unknown)';
if isfield(data, 'StartTime') && ~isempty(data.StartTime)
    startedStr = datestr(data.StartTime, 'yyyy-mm-dd HH:MM:SS');
end

infoLines = {
    sprintf('Engine: %s', engineName), ...
    sprintf('Started: %s', startedStr), ...
    sprintf('GUI elapsed: %s', elapsedStr), ...
    sprintf('Python start: %s', pythonStartedStr), ...
    sprintf('Python elapsed: %s', pythonElapsedStr)
};

helperInfo = slap2_launcher_fetch_helper_info();

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

function slap2_launcher_timer_tick(fig)
%SLAP2_LAUNCHER_TIMER_TICK Periodic refresh for elapsed time display.

slap2_launcher_refresh_info(fig);
end

function folder = slap2_launcher_get_session_folder()
%SLAP2_LAUNCHER_GET_SESSION_FOLDER Retrieve session folder from base workspace.

folder = '';
try
    existsFlag = evalin('base', 'exist(''SLAP2_SESSION_FOLDER'', ''var'')');
    if existsFlag
        folderValue = evalin('base', 'SLAP2_SESSION_FOLDER');
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

function info = slap2_launcher_fetch_helper_info()
%SLAP2_LAUNCHER_FETCH_HELPER_INFO Retrieve helper metadata from base workspace.

info = struct();

try
    existsFlag = evalin('base', 'exist(''SLAP2_MATLAB_HELPER_INFO'', ''var'')');
    if existsFlag
        candidate = evalin('base', 'SLAP2_MATLAB_HELPER_INFO');
        if isstruct(candidate)
            info = candidate;
        end
    end
catch
    info = struct();
end
end

function slap2_launcher_close_ui(fig)
%SLAP2_LAUNCHER_CLOSE_UI Close and invalidate the SLAP2 UI figure.

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

function elapsedStr = slap2_launcher_format_elapsed(startTime)
%SLAP2_LAUNCHER_FORMAT_ELAPSED Format elapsed time as HH:MM:SS.

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


function slap2_launcher_signal_complete(fig)
%SLAP2_LAUNCHER_SIGNAL_COMPLETE Notify Python that MATLAB is finished.

if isempty(fig) || ~isvalid(fig)
    return;
end

assignin('base', 'SLAP2_LAUNCHER_COMPLETED', true);
slap2_launcher_set_pending_stage('none');
slap2_launcher_update_status(fig, 'Completion signaled. Python will continue.');

data = fig.UserData;
if isfield(data, 'StartStopButton') && isvalid(data.StartStopButton)
    data.StartStopButton.Text = 'SLAP2 acquisition ended';
    data.StartStopButton.Enable = 'off';
end
data.StartStopState = 'finished';
fig.UserData = data;

if strcmpi(fig.WaitStatus, 'waiting')
    uiresume(fig);
end

if ~slap2_launcher_is_python_controlled(fig) && slap2_launcher_manual_completion_pending(fig)
    slap2_launcher_set_manual_completion_pending(fig, false);
    slap2_launcher_close_ui(fig);
end

end

function slap2_launcher_close_request(fig)
%SLAP2_LAUNCHER_CLOSE_REQUEST Handle manual closure of the UI.

if isempty(fig) || ~isvalid(fig)
    return;
end

if strcmpi(fig.WaitStatus, 'waiting')
    uiresume(fig);
end

slap2_launcher_close_ui(fig);
end


function slap2_launcher_ensure_launcher_path()
%SLAP2_LAUNCHER_ENSURE_LAUNCHER_PATH Keep the launcher directory on MATLAB path.

persistent pathEnsured
if ~isempty(pathEnsured) && pathEnsured
    return;
end

currentFile = mfilename('fullpath');
if isempty(currentFile)
    return;
end

launcherDir = fileparts(currentFile);
if isempty(launcherDir) || exist(launcherDir, 'dir') ~= 7
    return;
end

pathEntries = regexp(path, pathsep, 'split'); %#ok<RPTR>
launcherOnPath = any(cellfun(@(entry) strcmpi(strtrim(char(entry)), launcherDir), pathEntries));
if ~launcherOnPath
    addpath(launcherDir);
    rehash('path');
end

pathEnsured = true;
end


function [resumeMode, cleanedArgs] = slap2_launcher_extract_resume_flag(args)
%SLAP2_LAUNCHER_EXTRACT_RESUME_FLAG Remove and evaluate the resume flag.

resumeMode = false;
cleanedArgs = args;

idx = 1;
while idx <= numel(cleanedArgs) - 1
    key = cleanedArgs{idx};
    if ischar(key) || isstring(key)
        keyLower = lower(char(key));
        if strcmp(keyLower, 'resume')
            resumeMode = slap2_launcher_to_logical(cleanedArgs{idx + 1});
            cleanedArgs(idx:idx + 1) = [];
            break;
        end
    end
    idx = idx + 1;
end
end


function [stage, cleanedArgs] = slap2_launcher_extract_resume_stage(args)
%SLAP2_LAUNCHER_EXTRACT_RESUME_STAGE Parse requested resume stage keyword.

stage = 'start';
cleanedArgs = args;

idx = 1;
while idx <= numel(cleanedArgs) - 1
    key = cleanedArgs{idx};
    if ischar(key) || isstring(key)
        keyLower = lower(char(key));
        if strcmp(keyLower, 'resume_stage')
            stageCandidate = lower(strtrim(slap2_launcher_to_text(cleanedArgs{idx + 1}))); %#ok<STREMP>
            if any(strcmp(stageCandidate, {'completion', 'start'}))
                stage = stageCandidate;
            else
                stage = 'start';
            end
            cleanedArgs(idx:idx + 1) = [];
            break;
        end
    end
    idx = idx + 1;
end
end


function [value, cleanedArgs] = slap2_launcher_extract_named_arg(args, name)
%SLAP2_LAUNCHER_EXTRACT_NAMED_ARG Remove a name/value pair from varargin.

value = [];
cleanedArgs = args;

if nargin < 2 || isempty(name)
    return;
end

targetKey = lower(strtrim(slap2_launcher_to_text(name)));
if isempty(targetKey)
    return;
end

idx = 1;
while idx <= numel(cleanedArgs) - 1
    keyText = lower(strtrim(slap2_launcher_to_text(cleanedArgs{idx})));
    if ~isempty(keyText) && strcmp(keyText, targetKey)
        value = cleanedArgs{idx + 1};
        cleanedArgs(idx:idx + 1) = [];
        break;
    end
    idx = idx + 1;
end
end


function tf = slap2_launcher_to_logical(value)
%SLAP2_LAUNCHER_TO_LOGICAL Convert assorted inputs to logical true/false.

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


function text = slap2_launcher_to_text(value)
%SLAP2_LAUNCHER_TO_TEXT Convert assorted inputs (including py.str) to char.

text = '';
if nargin < 1 || isempty(value)
    return;
end

if ischar(value)
    text = value;
    return;
end

if isstring(value)
    text = char(value);
    return;
end

try
    textCandidate = char(value);
    if ischar(textCandidate)
        text = textCandidate;
        return;
    end
catch
end

try
    text = char(string(value));
catch
    text = '';
end
end


function outputs = slap2_launcher_prepare_outputs(count, varargin)
%SLAP2_LAUNCHER_PREPARE_OUTPUTS Return output cell array seeded with defaults.

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


function version = slap2_launcher_version()
%SLAP2_LAUNCHER_VERSION Return the MATLAB launcher UI version string.

version = '2025.12.05-1';
end


function version = slap2_launcher_helper_version()
%SLAP2_LAUNCHER_HELPER_VERSION Return the consolidated helper version string.

version = slap2_launcher_version();
end



function slap2_launcher_set_pending_stage(stage)
%SLAP2_LAUNCHER_SET_PENDING_STAGE Persist pending launcher state in base workspace.

pendingValue = lower(strtrim(slap2_launcher_to_text(stage)));
if isempty(pendingValue)
    pendingValue = 'none';
end

assignin('base', 'SLAP2_LAUNCHER_PENDING_STAGE', pendingValue);
end


function stage = slap2_launcher_get_pending_stage()
%SLAP2_LAUNCHER_GET_PENDING_STAGE Retrieve pending launcher state from base workspace.

stage = 'none';
try
    existsFlag = evalin('base', 'exist(''SLAP2_LAUNCHER_PENDING_STAGE'', ''var'')');
    if existsFlag
        stageValue = evalin('base', 'SLAP2_LAUNCHER_PENDING_STAGE');
        textValue = lower(strtrim(slap2_launcher_to_text(stageValue)));
        if ~isempty(textValue)
            stage = textValue;
        end
    end
catch
    stage = 'none';
end
end