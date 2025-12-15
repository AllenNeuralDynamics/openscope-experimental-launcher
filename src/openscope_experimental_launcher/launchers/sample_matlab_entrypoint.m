function sample_matlab_entrypoint(sessionFolder, varargin)
%SAMPLE_MATLAB_ENTRYPOINT Minimal MATLAB entry point for launcher testing.
%   sample_matlab_entrypoint(SESSIONFOLDER, ...) simulates a simple
%   acquisition loop, prints status messages, handles the optional resume
%   flag, and drops a heartbeat file in the session directory.

if nargin < 1 || isempty(sessionFolder)
    sessionFolder = pwd;
end

resumeMode = false;
idx = 1;
while idx <= numel(varargin) - 1
    key = varargin{idx};
    if ischar(key) || isstring(key)
        if strcmpi(string(key), 'resume')
            resumeMode = logical(varargin{idx + 1});
            varargin(idx:idx + 1) = [];
            break;
        end
    end
    idx = idx + 1;
end

fprintf('[SLAP2] sample_matlab_entrypoint running in %s\n', sessionFolder);
if resumeMode
    fprintf('[SLAP2] Resume flag detected; continuing previous session.\n');
else
    fprintf('[SLAP2] Fresh acquisition attempt.\n');
end

if ~isempty(varargin)
    fprintf('[SLAP2] Additional arguments:\n');
    disp(varargin);
end

if isfolder(sessionFolder)
    heartbeatFile = fullfile(sessionFolder, 'matlab_heartbeat.txt');
    fid = fopen(heartbeatFile, 'a');
    if fid ~= -1
        cleanupObj = onCleanup(@() fclose(fid)); %#ok<NASGU>
        fprintf(fid, 'MATLAB heartbeat at %s\n', datestr(now));
    else
        warning('SampleMatlabEntry:HeartbeatFailed', ...
            'Unable to open heartbeat file in %s', sessionFolder);
    end
else
    warning('SampleMatlabEntry:MissingSessionFolder', ...
        'Session folder "%s" does not exist.', sessionFolder);
end

pause(1);
fprintf('[SLAP2] sample_matlab_entrypoint complete.\n');
end
