-- calfetch.koplugin: fetch the daily screensaver calendar image.
-- Downloads calendar.png from a fixed public URL once a day (on KOReader
-- start / resume when the cached file is stale) into koreader/calendar.png.
-- Point KOReader's screensaver image setting at that file once; every
-- overwrite then shows up as the new sleep screen automatically.

local DataStorage = require("datastorage")
local InfoMessage = require("ui/widget/infomessage")
local NetworkMgr = require("ui/network/manager")
local UIManager = require("ui/uimanager")
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local https = require("ssl.https")
local lfs = require("libs/libkoreader-lfs")
local logger = require("logger")
local ltn12 = require("ltn12")
local _ = require("gettext")

local IMAGE_URL = "https://raw.githubusercontent.com/pennyasu/kindle-calendar/main/calendar.png"
local TARGET = DataStorage:getDataDir() .. "/calendar.png"

local CalFetch = WidgetContainer:extend{
    name = "calfetch",
    is_doc_only = false,
}

local function is_stale()
    local attr = lfs.attributes(TARGET)
    if not attr or not attr.modification then
        return true
    end
    local now = os.date("*t")
    local mod = os.date("*t", attr.modification)
    return now.year ~= mod.year or now.yday ~= mod.yday
end

local function download()
    local tmp = TARGET .. ".tmp"
    local file = io.open(tmp, "wb")
    if not file then return false end
    local ok, code = pcall(function()
        local _, status = https.request{
            url = IMAGE_URL,
            method = "GET",
            sink = ltn12.sink.file(file),
            protocol = "tlsv1_2",
        }
        return status
    end)
    if not ok or code ~= 200 then
        logger.warn("calfetch: download failed", ok, code)
        os.remove(tmp)
        return false
    end
    local attr = lfs.attributes(tmp)
    if not attr or (attr.size or 0) < 10000 then
        logger.warn("calfetch: downloaded file suspiciously small")
        os.remove(tmp)
        return false
    end
    os.remove(TARGET)
    local renamed = os.rename(tmp, TARGET)
    if not renamed then
        os.remove(tmp)
        return false
    end
    logger.info("calfetch: calendar.png updated")
    return true
end

function CalFetch:fetch(manual)
    if not NetworkMgr:isOnline() then
        if manual then
            UIManager:show(InfoMessage:new{ text = _("屏保日历：当前没有网络。") })
        end
        return false
    end
    local ok = download()
    if manual then
        UIManager:show(InfoMessage:new{
            text = ok and _("屏保日历已更新到今天。") or _("屏保日历更新失败，请稍后再试。"),
        })
    end
    return ok
end

function CalFetch:maybeFetch()
    if is_stale() then
        if NetworkMgr:isOnline() then
            self:fetch(false)
        else
            -- Retry in 15 minutes; KOReader may still be connecting to Wi-Fi.
            UIManager:scheduleIn(900, function() self:maybeFetch() end)
        end
    end
end

function CalFetch:init()
    UIManager:scheduleIn(15, function() self:maybeFetch() end)
end

function CalFetch:onResume()
    self:maybeFetch()
end

function CalFetch:addToMainMenu(menu_items)
    menu_items.calfetch_update = {
        text = _("更新屏保日历"),
        sorting_hint = "tools",
        callback = function()
            self:fetch(true)
        end,
    }
end

return CalFetch
