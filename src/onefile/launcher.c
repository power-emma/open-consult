/* Single-file consult-gui.exe for Windows: unpacks the GTK app appended to this .exe
 * (see onefile.h) to %LOCALAPPDATA%\open-consult\gui-<hash> on first run, then runs it.
 * Later runs of the same build start it straight from there. Logs still go to logs\
 * next to this .exe, through CONSULT_LOG_DIR. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <zlib.h>

#include "onefile.h"

static void fail(const wchar_t *what, DWORD code)
{
    wchar_t msg[1024], sys[512] = L"";
    if (code)
        FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, NULL, code, 0,
                       sys, sizeof sys / sizeof *sys, NULL);
    _snwprintf(msg, sizeof msg / sizeof *msg, L"%ls\n\n%ls", what, sys);
    msg[sizeof msg / sizeof *msg - 1] = 0;
    MessageBoxW(NULL, msg, L"consult-gui", MB_ICONERROR);
    ExitProcess(1);
}

static int exists(const wchar_t *path)
{
    return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES;
}

/* Best effort: a folder still in use by a running copy just stays. */
static void remove_tree(const wchar_t *dir)
{
    wchar_t pat[MAX_PATH], sub[MAX_PATH];
    WIN32_FIND_DATAW fd;
    HANDLE h;

    _snwprintf(pat, MAX_PATH, L"%ls\\*", dir);
    if ((h = FindFirstFileW(pat, &fd)) != INVALID_HANDLE_VALUE) {
        do {
            if (!wcscmp(fd.cFileName, L".") || !wcscmp(fd.cFileName, L".."))
                continue;
            _snwprintf(sub, MAX_PATH, L"%ls\\%ls", dir, fd.cFileName);
            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
                remove_tree(sub);
            else
                DeleteFileW(sub);
        } while (FindNextFileW(h, &fd));
        FindClose(h);
    }
    RemoveDirectoryW(dir);
}

/* Remove unpacked copies of older builds. */
static void remove_old(const wchar_t *base, const wchar_t *keep)
{
    wchar_t pat[MAX_PATH], dir[MAX_PATH];
    WIN32_FIND_DATAW fd;
    HANDLE h;

    _snwprintf(pat, MAX_PATH, L"%ls\\gui-*", base);
    if ((h = FindFirstFileW(pat, &fd)) == INVALID_HANDLE_VALUE)
        return;
    do {
        _snwprintf(dir, MAX_PATH, L"%ls\\%ls", base, fd.cFileName);
        if ((fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && _wcsicmp(dir, keep) != 0)
            remove_tree(dir);
    } while (FindNextFileW(h, &fd));
    FindClose(h);
}

/* Create every parent folder of path (path itself is a file). */
static void make_parents(wchar_t *path)
{
    for (wchar_t *p = path + 3; *p; p++)
        if (*p == L'\\') {
            *p = 0;
            CreateDirectoryW(path, NULL);
            *p = L'\\';
        }
}

static void unpack(const unsigned char *data, uint64_t size, const onefile_footer_t *f,
                   const wchar_t *dir)
{
    const unsigned char *p = data + f->payload_offset, *end = data + size - sizeof *f;

    for (uint32_t i = 0; i < f->count; i++) {
        uint16_t plen;
        uint32_t sizes[2];
        char rel[512];
        wchar_t wrel[512], path[MAX_PATH];
        unsigned char *raw;
        uLongf rn;
        HANDLE h;
        DWORD wrote;

        if (end - p < 2)
            fail(L"This consult-gui.exe is damaged (truncated file list).", 0);
        memcpy(&plen, p, 2);
        p += 2;
        if (plen >= sizeof rel || end - p < plen + 8)
            fail(L"This consult-gui.exe is damaged (bad entry).", 0);
        memcpy(rel, p, plen);
        rel[plen] = 0;
        p += plen;
        memcpy(sizes, p, 8);
        p += 8;
        if ((uint64_t)(end - p) < sizes[1] || strstr(rel, "..") || rel[0] == '/')
            fail(L"This consult-gui.exe is damaged (bad entry).", 0);
        for (char *c = rel; *c; c++)
            if (*c == '/')
                *c = '\\';
        if (!MultiByteToWideChar(CP_UTF8, 0, rel, -1, wrel, 512))
            fail(L"This consult-gui.exe is damaged (bad file name).", 0);
        _snwprintf(path, MAX_PATH, L"%ls\\%ls", dir, wrel);
        make_parents(path);

        rn = sizes[0];
        raw = HeapAlloc(GetProcessHeap(), 0, sizes[0] ? sizes[0] : 1);
        if (!raw || uncompress(raw, &rn, p, sizes[1]) != Z_OK || rn != sizes[0])
            fail(L"This consult-gui.exe is damaged (bad data).", 0);
        p += sizes[1];

        h = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (h == INVALID_HANDLE_VALUE || !WriteFile(h, raw, sizes[0], &wrote, NULL) ||
            wrote != sizes[0])
            fail(L"Couldn't unpack consult-gui to %LOCALAPPDATA%\\open-consult.", GetLastError());
        CloseHandle(h);
        HeapFree(GetProcessHeap(), 0, raw);
    }
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, LPWSTR cmd, int show)
{
    wchar_t self[MAX_PATH], base[MAX_PATH], dir[MAX_PATH], tmp[MAX_PATH], mark[MAX_PATH];
    wchar_t app[MAX_PATH], logs[MAX_PATH], *slash, *cmdline;
    HANDLE file, map;
    LARGE_INTEGER size;
    const unsigned char *data;
    onefile_footer_t f;
    STARTUPINFOW si = {.cb = sizeof si};
    PROCESS_INFORMATION pi;
    DWORD code = 0;

    (void)inst, (void)prev, (void)cmd, (void)show;
    if (!GetModuleFileNameW(NULL, self, MAX_PATH))
        fail(L"Can't find this program's own path.", GetLastError());

    /* Read the footer and map the payload. */
    file = CreateFileW(self, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (file == INVALID_HANDLE_VALUE || !GetFileSizeEx(file, &size))
        fail(L"Can't read this program's own file.", GetLastError());
    map = CreateFileMappingW(file, NULL, PAGE_READONLY, 0, 0, NULL);
    data = map ? MapViewOfFile(map, FILE_MAP_READ, 0, 0, 0) : NULL;
    if (!data)
        fail(L"Can't read this program's own file.", GetLastError());
    if ((uint64_t)size.QuadPart < sizeof f)
        fail(L"This consult-gui.exe has no app inside (built with make onefile?).", 0);
    memcpy(&f, data + size.QuadPart - sizeof f, sizeof f);
    if (memcmp(f.magic, ONEFILE_MAGIC, sizeof f.magic) != 0 ||
        f.payload_offset > (uint64_t)size.QuadPart - sizeof f)
        fail(L"This consult-gui.exe has no app inside (built with make onefile?).", 0);

    /* %LOCALAPPDATA%\open-consult\gui-<hash>, unpacked once per build. */
    if (!GetEnvironmentVariableW(L"LOCALAPPDATA", base, MAX_PATH))
        fail(L"%LOCALAPPDATA% isn't set.", 0);
    wcscat(base, L"\\open-consult");
    CreateDirectoryW(base, NULL);
    _snwprintf(dir, MAX_PATH, L"%ls\\gui-%016llx", base, (unsigned long long)f.hash);
    _snwprintf(mark, MAX_PATH, L"%ls\\.complete", dir);
    if (!exists(mark)) {
        _snwprintf(tmp, MAX_PATH, L"%ls.tmp%lu", dir, GetCurrentProcessId());
        remove_tree(tmp);
        if (!CreateDirectoryW(tmp, NULL))
            fail(L"Couldn't create a folder in %LOCALAPPDATA%\\open-consult.", GetLastError());
        unpack(data, (uint64_t)size.QuadPart, &f, tmp);
        _snwprintf(mark, MAX_PATH, L"%ls\\.complete", tmp);
        CloseHandle(CreateFileW(mark, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL));
        if (exists(dir))
            remove_tree(dir);           /* a half-unpacked folder from an interrupted run */
        if (!MoveFileExW(tmp, dir, 0)) {
            DWORD err = GetLastError();
            _snwprintf(mark, MAX_PATH, L"%ls\\.complete", dir);
            remove_tree(tmp);
            if (!exists(mark))          /* not just another copy that got there first */
                fail(L"Couldn't unpack consult-gui to %LOCALAPPDATA%\\open-consult.", err);
        }
        remove_old(base, dir);
    }
    UnmapViewOfFile(data);
    CloseHandle(map);
    CloseHandle(file);

    /* Logs next to this .exe, as with the folder build. */
    if (!GetEnvironmentVariableW(L"CONSULT_LOG_DIR", logs, MAX_PATH)) {
        wcscpy(logs, self);
        if ((slash = wcsrchr(logs, L'\\')))
            wcscpy(slash + 1, L"logs");
        SetEnvironmentVariableW(L"CONSULT_LOG_DIR", logs);
    }

    _snwprintf(app, MAX_PATH, L"%ls\\" ONEFILE_MAIN_W, dir);
    cmdline = _wcsdup(GetCommandLineW());
    if (!CreateProcessW(app, cmdline, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
        fail(L"Couldn't start consult-gui.", GetLastError());
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)code;
}
