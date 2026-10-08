-- Run the shipping ROM through Mesen 2.1.1. Real controller input, not a second
-- implementation of the game. Output and screenshots stay in this workspace.
local root = assert(os.getenv("GFC_ROOT")):gsub("\\", "/")
local log = assert(io.open(root .. "/build/verification.txt", "w"))
local stop = emu.exit or emu.stop
local symbols = {}
for line in io.lines(root .. "/build/gfc.sym") do
    local address, name = line:match("^([%x]+)%s+(.+)$")
    if address then symbols[name] = tonumber(address, 16) end
end
local function addr(name)
    return assert(symbols[name], "Missing symbol " .. name)
end
local function read(name)
    return emu.read(addr(name), emu.memType.snesDebug)
end
local function read16(name)
    return emu.read16(addr(name), emu.memType.snesDebug)
end
local checks = 0
local dsp = {}
local soundSources = {[0]={},[1]={},[2]={}}
local soundKeyOns = 0
-- Observe the actual SPC700's DSP writes: each outcome must trigger audible
-- voices, and the click, buzz, and replacement must use different samples.
emu.addMemoryCallback(function(_, value)
    local reg = emu.read(0xf2, emu.memType.spcDebug)
    dsp[reg] = value
    if reg == 0x4c and value ~= 0 and read("gfcReady") == 1 then
        soundKeyOns = soundKeyOns + 1
        local result = read("gfcLastResult")
        for voice=1,7 do
            if (value & (1 << voice)) ~= 0 then
                local source = dsp[voice*16+4]
                if source then soundSources[result][source] = true end
            end
        end
    end
end, emu.callbackType.write, 0xf3, 0xf3, emu.cpuType.spc, emu.memType.spcMemory)
local function check(ok, message)
    checks = checks + 1
    if not ok then error(message) end
end
local desired = {}
emu.addEventCallback(function()
    local input = emu.getInput(0)
    for name in pairs(input) do input[name] = desired[name:lower()] == true end
    emu.setInput(input, 0)
end, emu.eventType.inputPolled)

local function wait(frames)
    for _ = 1, frames do coroutine.yield() end
end
local function press(button, frames)
    desired = {[button] = true}
    wait(frames or 3)
    desired = {}
    wait(3)
end
local function screenshot(name)
    local file = assert(io.open(root .. "/build/screenshots/" .. name .. ".png", "wb"))
    file:write(emu.takeScreenshot())
    file:close()
end
local routes = {
    [1] = {"b"}, [2] = {"b", "a", "x"}, [3] = {"b", "a"},
    [4] = {"x"}, [5] = {}, [6] = {"x", "a"},
}
local pools = {[1]=0,[2]=1,[4]=2,[3]=3,[5]=4,[6]=5}
local names = {[1]="fast",[2]="cheap",[4]="good",[3]="fast-cheap",[5]="fast-good",[6]="cheap-good"}
local buttons = {{"x",1},{"a",2},{"b",4}}
local function go(state)
    press("start")
    for _,button in ipairs(routes[state]) do press(button) end
    check(read("gfcState") == state, "Cannot reach state " .. state .. "; got " .. read("gfcState"))
end
local commentBase
for name,address in pairs(symbols) do
    if name:match("_gfcComments$") then commentBase = address end
end
assert(commentBase, "Comment array not found")
local function checkComment()
    local state, pool, index = read("gfcState"), read("gfcCommentPool"), read("gfcCommentIndex")
    check(pool == pools[state], "Comment chosen from wrong state pool")
    check(index < 24, "Comment index outside pool")
    -- Compare displayed glyphs against the selected comment in the ROM's array.
    for line=0,1 do
        local ended = false
        for col=0,27 do
            local ch = emu.read(commentBase + ((pool*24+index)*2+line)*29+col, emu.memType.snesDebug)
            if ch == 0 then ended = true end
            local tile = emu.read16(addr("textMap") + ((21+line*2)*32+2+col)*2, emu.memType.snesDebug) & 1023
            check(tile == (ended and 0 or ch-32), "Comment render mismatch")
        end
    end
end

local function checkSliders()
    for row,bit in ipairs({4,1,2}) do -- GOOD, FAST, CHEAP
        local on = (read("gfcState") & bit) ~= 0
        local rail = emu.read16(addr("textMap") + ((7+(row-1)*4)*32+18)*2, emu.memType.snesDebug)
        check((rail ~= 0) == on, "White rail assigned to wrong slider row")
        local word = on and "ON " or "OFF"
        for col=1,3 do
            local tile = emu.read16(addr("textMap") + ((8+(row-1)*4)*32+13+col)*2, emu.memType.snesDebug) & 1023
            check(tile == word:byte(col)-32, "ON/OFF label assigned to wrong slider row")
        end
        local x = emu.read16(addr("knobX")+(row-1)*2, emu.memType.snesDebug)
        check(x == (on and 184 or 152), "Knob position assigned to wrong slider row")
    end
end

local task = coroutine.create(function()
    local bootFrames = 0
    while read("gfcReady") ~= 1 do
        wait(1)
        bootFrames = bootFrames + 1
        check(bootFrames < 600, "ROM did not finish startup")
    end
    wait(20)
    check(read("gfcState") == 5, "Default is not FAST + GOOD")
    checkComment()
    screenshot("default")
    log:write("PASS: boot, default FAST + GOOD, native screen capture\n"); log:flush()

    for state=1,6 do
        go(state)
        wait(10)
        checkComment()
        checkSliders()
        screenshot(names[state])
        for _,button in ipairs(buttons) do
            go(state)
            local count = read16("gfcChangeCount")
            press(button[1])
            local nextState, result = read("gfcState"), read("gfcLastResult")
            if state == button[2] then
                check(nextState == state and result == 0, "Final switch must reject OFF")
                check(read16("gfcChangeCount") == count, "Reject counted as a change")
            elseif (state & button[2]) ~= 0 then
                check(nextState == (state ~ button[2]) and result == 1, "ON switch did not turn OFF")
                checkComment()
            elseif state == 1 or state == 2 or state == 4 then
                check(nextState == (state | button[2]) and result == 1, "Second switch did not turn ON")
                checkComment()
            else
                check((nextState & button[2]) ~= 0 and result == 2, "New third choice must stay ON")
                local remaining = nextState & state
                check(remaining ~= 0 and (remaining & (remaining-1)) == 0, "Must keep exactly one previous choice")
                checkComment()
            end
        end
    end
    log:write("PASS: all 18 state/button transitions, six screenshots, matching comment pools/text\n"); log:flush()

    go(5)
    local count = read16("gfcChangeCount")
    press("x", 90)
    check(read("gfcState") == 4 and read16("gfcChangeCount") == count+1, "Held button repeated")
    screenshot("held-x")
    go(1)
    press("x")
    screenshot("rejected")
    log:write("PASS: hold suppression and rejection screen\n"); log:flush()

    for state=1,6 do
        for combo=1,7 do
            go(state)
            desired = {x=(combo&1)~=0,a=(combo&2)~=0,b=(combo&4)~=0}
            wait(4)
            desired = {}
            wait(4)
            local value = read("gfcState")
            check(value>=1 and value<=6, "Simultaneous presses produced invalid state")
        end
    end
    desired = {x=true,a=true,b=true,start=true}
    wait(4)
    desired = {}
    wait(4)
    check(read("gfcState") == 5, "START must take priority over toggle edges")
    log:write("PASS: 42 simultaneous combinations and START priority\n"); log:flush()

    local kicks = {[3]=0,[6]=0}
    for trial=1,240 do
        go(5)
        wait(trial%11) -- reproducible variety of human-like press timing
        press("a")
        local value = read("gfcState")
        check(value == 3 or value == 6, "Third choice lost CHEAP")
        kicks[value] = kicks[value]+1
    end
    check(kicks[3]>80 and kicks[3]<160, "Kick distribution unexpectedly skewed")
    log:write("PASS: 240 random kicks; FAST retained "..kicks[3]..", GOOD retained "..kicks[6].."\n")
    go(5)
    wait(12)
    screenshot("final")
    check(soundKeyOns > 20, "No SNES DSP sound playback observed")
    local unique = {}
    for result=0,2 do
        local found = false
        for source in pairs(soundSources[result]) do unique[source]=true; found=true end
        check(found, "No sound source observed for outcome "..result)
    end
    local distinct = 0
    for _ in pairs(unique) do distinct=distinct+1 end
    check(distinct >= 3, "Three outcomes did not use distinct sound samples")
    log:write("PASS: SNES DSP played three distinct effect samples ("..soundKeyOns.." key-ons)\n")
    -- Observe two complete sample loops, including the continuation ROM bank.
    local wraps, previous = 0, nil
    for sample=1,180 do
        wait(10)
        local audio = emu.getState()
        check(audio["spc.dsp.voices[0].envOut"] > 0, "Background music stopped")
        local position = audio["spc.dsp.voices[0].brrAddress"]
        if previous and position < previous then wraps = wraps + 1 end
        previous = position
    end
    check(wraps >= 2, "Background music did not repeat twice")
    log:write("PASS: background music remains active through two complete loops\n")
    log:write("PASS: "..checks.." assertions; ROM input, state, comment, hold, reset, and random checks complete\n")
    log:close()
    stop(0) -- 2.1.1 calls this stop; later builds call it exit.
end)

local frames = 0
emu.addEventCallback(function()
    frames = frames + 1
    if read("gfcReady") == 1 then
        local state = read("gfcState")
        if state<1 or state>6 then
            log:write("FAIL: invalid state during frame "..frames.."\n"); log:close()
            stop(1)
            return
        end
    end
    if coroutine.status(task) ~= "dead" then
        local ok, err = coroutine.resume(task)
        if not ok then
            log:write("FAIL: "..tostring(err).."\n"); log:close()
            stop(1)
        end
    end
end, emu.eventType.endFrame)
