#include "PrintbenchNativePanel.hpp"

#include "DeviceManager.hpp"
#include "GUI_App.hpp"
#include "MainFrame.hpp"
#include "DeviceCore/DevLamp.h"
#include "MediaPlayCtrl.h"
#include "wxMediaCtrl2.h"
#include "wxExtensions.hpp"

#include <algorithm>
#include <array>
#include <deque>
#include <fstream>
#include <wx/datetime.h>
#include <wx/filename.h>
#include <wx/stdpaths.h>
#include <wx/textfile.h>
#include <wx/dcbuffer.h>
#include <wx/sizer.h>
#include <wx/statline.h>
#include <wx/msgdlg.h>
#include <wx/gauge.h>

namespace Slic3r {
namespace GUI {

namespace {
const wxColour PB_BG(2, 10, 20);
const wxColour PB_CARD(6, 20, 33);
const wxColour PB_BORDER(20, 52, 76);
const wxColour PB_TEXT(236, 245, 252);
const wxColour PB_MUTED(111, 137, 158);
const wxColour PB_ACCENT(0, 188, 230);
const wxColour PB_OK(68, 214, 151);

enum : int {
    ID_PB_CAMERA_RECORD = wxID_HIGHEST + 4101,
    ID_PB_CAMERA_TIMELAPSE,
    ID_PB_CAMERA_RESOLUTION
};

void style_label(wxStaticText* label, int point_size, bool bold = false, const wxColour& colour = PB_TEXT)
{
    wxFont font = label->GetFont();
    font.SetPointSize(point_size);
    font.SetWeight(bold ? wxFONTWEIGHT_BOLD : wxFONTWEIGHT_NORMAL);
    label->SetFont(font);
    label->SetForegroundColour(colour);
}

wxString format_temp(double value, double target = -1.0)
{
    if (target >= 0.0)
        return wxString::Format("%.0f C  /  %.0f C", value, target);
    return wxString::Format("%.0f C", value);
}
} // namespace

class PrintbenchTempChart : public wxPanel
{
public:
    explicit PrintbenchTempChart(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetBackgroundColour(wxColour(7, 21, 31));
        SetMinSize(wxSize(FromDIP(300), FromDIP(115)));
        Bind(wxEVT_PAINT, &PrintbenchTempChart::on_paint, this);
    }

    void push(double nozzle, double bed, double chamber)
    {
        const std::array<double, 3> sample{nozzle, bed, chamber};
        m_samples.push_back(sample);
        while (m_samples.size() > 90)
            m_samples.pop_front();
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const auto size = GetClientSize();
        dc.SetBackground(wxBrush(GetBackgroundColour()));
        dc.Clear();
        if (size.x < 20 || size.y < 20)
            return;

        const int left = FromDIP(28);
        const int right = FromDIP(8);
        const int top = FromDIP(8);
        const int bottom = FromDIP(18);
        const int graph_w = std::max(1, size.x - left - right);
        const int graph_h = std::max(1, size.y - top - bottom);

        dc.SetPen(wxPen(wxColour(24, 51, 67), 1));
        for (int i = 0; i <= 4; ++i) {
            const int y = top + (graph_h * i) / 4;
            dc.DrawLine(left, y, left + graph_w, y);
        }
        for (int i = 0; i <= 6; ++i) {
            const int x = left + (graph_w * i) / 6;
            dc.DrawLine(x, top, x, top + graph_h);
        }

        double max_value = 40.0;
        for (const auto& sample : m_samples)
            max_value = std::max({max_value, sample[0], sample[1], sample[2]});
        max_value = std::min(320.0, std::ceil((max_value + 10.0) / 10.0) * 10.0);

        wxFont axis_font = GetFont();
        axis_font.SetPointSize(7);
        dc.SetFont(axis_font);
        dc.SetTextForeground(wxColour(85, 115, 132));
        for (int i = 0; i <= 4; ++i) {
            const int value = static_cast<int>(std::lround(max_value * (4 - i) / 4.0));
            const wxString label = wxString::Format("%d°", value);
            const wxSize ext = dc.GetTextExtent(label);
            dc.DrawText(label, std::max(0, left - ext.x - FromDIP(5)), top + (graph_h * i) / 4 - ext.y / 2);
        }
        const wxString older = "ALT";
        const wxString live = "LIVE";
        dc.DrawText(older, left, top + graph_h + FromDIP(3));
        const wxSize live_ext = dc.GetTextExtent(live);
        dc.DrawText(live, left + graph_w - live_ext.x, top + graph_h + FromDIP(3));

        if (m_samples.size() < 2)
            return;

        const std::array<wxColour, 3> colours{
            wxColour(0, 188, 230), wxColour(210, 222, 231), wxColour(90, 145, 165)};
        for (size_t series = 0; series < 3; ++series) {
            dc.SetPen(wxPen(colours[series], series == 0 ? std::max(2, FromDIP(2)) : 1));
            wxPoint previous;
            bool have_previous = false;
            wxPoint last;
            for (size_t i = 0; i < m_samples.size(); ++i) {
                const int x = left + static_cast<int>((static_cast<double>(i) / (m_samples.size() - 1)) * graph_w);
                const double normalized = std::clamp(m_samples[i][series] / max_value, 0.0, 1.0);
                const int y = top + graph_h - static_cast<int>(normalized * graph_h);
                const wxPoint point(x, y);
                if (have_previous)
                    dc.DrawLine(previous, point);
                previous = point;
                last = point;
                have_previous = true;
            }
            dc.SetPen(wxPen(colours[series], 1));
            dc.SetBrush(wxBrush(colours[series]));
            dc.DrawCircle(last, series == 0 ? FromDIP(3) : FromDIP(2));
        }
    }

    std::deque<std::array<double, 3>> m_samples;
};

class PrintbenchAmsSlotCard : public wxPanel
{
public:
    PrintbenchAmsSlotCard(wxWindow* parent, int slot)
        : wxPanel(parent, wxID_ANY), m_slot(slot)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetBackgroundColour(wxColour(7, 21, 31));
        SetMinSize(wxSize(FromDIP(86), FromDIP(112)));
        Bind(wxEVT_PAINT, &PrintbenchAmsSlotCard::on_paint, this);
    }

    void set_slot(bool present, const wxString& material, const wxColour& colour, int remain)
    {
        m_present = present;
        m_material = material.empty() ? (present ? "FILAMENT" : "LEER") : material;
        m_colour = colour;
        m_remain = remain;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(GetBackgroundColour()));
        dc.Clear();
        if (size.x < 20 || size.y < 20) return;

        dc.SetPen(wxPen(PB_BORDER, 1));
        dc.SetBrush(wxBrush(wxColour(8, 25, 37)));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(6));

        wxFont tiny = GetFont();
        tiny.SetPointSize(8); tiny.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(tiny);
        dc.SetTextForeground(PB_MUTED);
        dc.DrawText(wxString::Format("SLOT %d", m_slot), FromDIP(8), FromDIP(6));

        if (m_remain >= 0 && m_present) {
            const wxString pct = wxString::Format("%d %%", m_remain);
            const wxSize ext = dc.GetTextExtent(pct);
            dc.DrawText(pct, size.x - ext.x - FromDIP(8), FromDIP(6));
        }

        const int cx = size.x / 2;
        const int cy = FromDIP(45);
        const int outer = FromDIP(22);
        const int inner = FromDIP(8);
        if (m_present) {
            dc.SetPen(wxPen(m_colour.ChangeLightness(78), std::max(1, FromDIP(2))));
            dc.SetBrush(wxBrush(m_colour));
            dc.DrawCircle(cx, cy, outer);
            dc.SetPen(wxPen(wxColour(18, 40, 53), std::max(1, FromDIP(2))));
            dc.SetBrush(wxBrush(wxColour(5, 17, 27)));
            dc.DrawCircle(cx, cy, inner);
            dc.SetPen(wxPen(wxColour(220, 232, 240), 1));
            dc.DrawCircle(cx, cy, std::max(2, FromDIP(3)));
        } else {
            dc.SetPen(wxPen(PB_BORDER, std::max(1, FromDIP(2)), wxPENSTYLE_SHORT_DASH));
            dc.SetBrush(*wxTRANSPARENT_BRUSH);
            dc.DrawCircle(cx, cy, outer);
            dc.DrawCircle(cx, cy, inner);
        }

        wxFont material_font = GetFont();
        material_font.SetPointSize(9); material_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(material_font);
        dc.SetTextForeground(m_present ? PB_TEXT : PB_MUTED);
        wxString material = m_material;
        while (!material.empty() && dc.GetTextExtent(material).x > size.x - FromDIP(12))
            material.RemoveLast();
        if (material != m_material && material.length() > 1) {
            material.RemoveLast();
            material += wxString::FromUTF8("…");
        }
        wxSize material_ext = dc.GetTextExtent(material);
        dc.DrawText(material, std::max(FromDIP(5), (size.x - material_ext.x) / 2), FromDIP(72));
        dc.SetFont(tiny);
        dc.SetTextForeground(PB_MUTED);
        const wxString detail = m_present
            ? (m_remain >= 0 ? wxString::Format("%d %% Rest", m_remain) : wxString("AMS 2 Pro"))
            : wxString("Kein Filament");
        wxSize detail_ext = dc.GetTextExtent(detail);
        dc.DrawText(detail, std::max(FromDIP(5), (size.x - detail_ext.x) / 2), FromDIP(89));

        if (m_present) {
            dc.SetPen(*wxTRANSPARENT_PEN);
            dc.SetBrush(wxBrush(m_colour));
            dc.DrawRoundedRectangle(FromDIP(8), size.y - FromDIP(7), size.x - FromDIP(16), FromDIP(3), FromDIP(2));
        }
    }

    int m_slot{1};
    bool m_present{false};
    wxString m_material{"LEER"};
    wxColour m_colour{40, 62, 75};
    int m_remain{-1};
};

class PrintbenchHeroPanel : public wxPanel
{
public:
    PrintbenchHeroPanel(wxWindow* parent, const wxBitmap& bitmap)
        : wxPanel(parent, wxID_ANY), m_source(bitmap.ConvertToImage())
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetBackgroundColour(PB_CARD);
        SetMinSize(wxSize(FromDIP(390), FromDIP(340)));
        Bind(wxEVT_PAINT, &PrintbenchHeroPanel::on_paint, this);
    }

    void SetSnapshot(bool online, const wxString& state)
    {
        const bool ready = online && (state == "IDLE" || state == "FINISH");
        const bool printing = online && state == "RUNNING";
        const bool paused = online && state == "PAUSE";
        m_online = online;
        m_state = state;
        m_pill = ready ? "BEREIT" : (printing ? "DRUCKT" : (paused ? "PAUSE" : (online ? "ONLINE" : "OFFLINE")));
        m_status = ready ? "Bereit zum Drucken"
                         : (online ? (state.empty() ? "Verbunden im LAN" : state) : "Nicht verbunden");
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (!m_source.IsOk() || size.x < 20 || size.y < 20)
            return;

        const double aspect = static_cast<double>(m_source.GetWidth()) / std::max(1, m_source.GetHeight());
        int draw_w = size.x;
        int draw_h = static_cast<int>(draw_w / aspect);
        if (draw_h > size.y) {
            draw_h = size.y;
            draw_w = static_cast<int>(draw_h * aspect);
        }
        const int ox = (size.x - draw_w) / 2;
        const int oy = (size.y - draw_h) / 2;
        if (!m_cache.IsOk() || m_cache_size != wxSize(draw_w, draw_h)) {
            m_cache = wxBitmap(m_source.Scale(draw_w, draw_h, wxIMAGE_QUALITY_HIGH));
            m_cache_size = wxSize(draw_w, draw_h);
        }
        dc.DrawBitmap(m_cache, ox, oy, false);

        const auto px = [&](double fraction) { return ox + static_cast<int>(fraction * draw_w); };
        const auto py = [&](double fraction) { return oy + static_cast<int>(fraction * draw_h); };

        wxFont title = GetFont();
        title.SetPointSize(18);
        title.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(title);
        dc.SetTextForeground(PB_TEXT);
        dc.DrawText("Bambu Lab P2S", px(0.025), py(0.025));

        wxFont pill_font = GetFont();
        pill_font.SetPointSize(8);
        pill_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(pill_font);
        const wxSize pill_ext = dc.GetTextExtent(m_pill);
        const int pill_x = px(0.40);
        const int pill_y = py(0.035);
        const int pill_w = pill_ext.x + FromDIP(14);
        const int pill_h = pill_ext.y + FromDIP(6);
        const wxColour pill_fill = !m_online ? wxColour(35, 48, 58)
                                : (m_state == "PAUSE" ? wxColour(103, 70, 24) : wxColour(18, 91, 68));
        const wxColour pill_text = !m_online ? PB_MUTED
                                : (m_state == "PAUSE" ? wxColour(255, 207, 117) : wxColour(112, 239, 190));
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(pill_fill));
        dc.DrawRoundedRectangle(pill_x, pill_y, pill_w, pill_h, FromDIP(5));
        dc.SetTextForeground(pill_text);
        dc.DrawText(m_pill, pill_x + FromDIP(7), pill_y + FromDIP(3));

        wxFont state_font = GetFont();
        state_font.SetPointSize(9);
        state_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(state_font);
        dc.SetTextForeground(m_online ? PB_OK : PB_MUTED);
        const wxString bullet = wxString(L"\u25CF  ") + m_status;
        dc.DrawText(bullet, px(0.025), py(0.17));
    }

    wxImage m_source;
    wxBitmap m_cache;
    wxSize m_cache_size;
    bool m_online{false};
    wxString m_state;
    wxString m_pill{"OFFLINE"};
    wxString m_status{"Nicht verbunden"};
};

class PrintbenchJobHeader : public wxPanel
{
public:
    explicit PrintbenchJobHeader(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(260), FromDIP(62)));
        Bind(wxEVT_PAINT, &PrintbenchJobHeader::on_paint, this);
    }

    void SetJob(const wxString& name, const wxString& print_state, bool active)
    {
        m_name = active && !name.empty() ? name : "Kein aktiver Druck";
        m_state = print_state;
        m_active = active;
        Refresh(false);
    }

private:
    static wxString fit_text(wxDC& dc, wxString text, int max_width)
    {
        if (max_width <= 0 || dc.GetTextExtent(text).x <= max_width)
            return text;
        const wxString ellipsis = wxString::FromUTF8("…");
        while (!text.empty() && dc.GetTextExtent(text + ellipsis).x > max_width)
            text.RemoveLast();
        return text + ellipsis;
    }

    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x < FromDIP(120) || size.y < FromDIP(40))
            return;

        const int thumb = std::min(FromDIP(48), size.y - FromDIP(10));
        const int tx = FromDIP(4);
        const int ty = std::max(0, (size.y - thumb) / 2);
        dc.SetPen(wxPen(wxColour(30, 80, 106), 1));
        dc.SetBrush(wxBrush(wxColour(5, 38, 58)));
        dc.DrawRoundedRectangle(tx, ty, thumb, thumb, FromDIP(6));

        const int cx = tx + thumb / 2;
        const int cy = ty + thumb / 2 + FromDIP(2);
        dc.SetPen(wxPen(PB_ACCENT, std::max(1, FromDIP(2))));
        dc.SetBrush(wxBrush(wxColour(0, 98, 137)));
        wxPoint model[6]{{cx - FromDIP(11), cy + FromDIP(7)}, {cx - FromDIP(8), cy - FromDIP(7)},
                         {cx, cy - FromDIP(12)}, {cx + FromDIP(10), cy - FromDIP(5)},
                         {cx + FromDIP(8), cy + FromDIP(9)}, {cx - FromDIP(4), cy + FromDIP(12)}};
        dc.DrawPolygon(6, model);

        wxString badge = "BEREIT";
        wxColour badge_fill(23, 55, 70);
        wxColour badge_text = PB_MUTED;
        if (m_active && m_state == "PAUSE") {
            badge = "PAUSE";
            badge_fill = wxColour(104, 72, 25);
            badge_text = wxColour(255, 208, 122);
        } else if (m_active) {
            badge = "DRUCKT";
            badge_fill = wxColour(20, 91, 70);
            badge_text = wxColour(111, 238, 189);
        }

        wxFont badge_font = GetFont();
        badge_font.SetPointSize(8);
        badge_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(badge_font);
        const wxSize badge_ext = dc.GetTextExtent(badge);
        const int badge_w = badge_ext.x + FromDIP(16);
        const int badge_h = badge_ext.y + FromDIP(7);
        const int badge_x = size.x - badge_w - FromDIP(3);
        const int badge_y = FromDIP(7);
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(badge_fill));
        dc.DrawRoundedRectangle(badge_x, badge_y, badge_w, badge_h, FromDIP(5));
        dc.SetTextForeground(badge_text);
        dc.DrawText(badge, badge_x + FromDIP(8), badge_y + FromDIP(3));

        const int text_x = tx + thumb + FromDIP(10);
        const int text_right = badge_x - FromDIP(8);
        wxFont name_font = GetFont();
        name_font.SetPointSize(14);
        name_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(name_font);
        dc.SetTextForeground(PB_TEXT);
        dc.DrawText(fit_text(dc, m_name, text_right - text_x), text_x, FromDIP(6));

        wxFont meta_font = GetFont();
        meta_font.SetPointSize(9);
        dc.SetFont(meta_font);
        dc.SetTextForeground(PB_MUTED);
        dc.DrawText("Bambu Lab P2S  •  lokaler Druckauftrag", text_x, FromDIP(34));
    }

    wxString m_name{"Kein aktiver Druck"};
    wxString m_state;
    bool m_active{false};
};

class PrintbenchCameraTile : public wxPanel
{
public:
    PrintbenchCameraTile(wxWindow* parent, int id, const wxString& caption)
        : wxPanel(parent, id), m_caption(caption)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(92), FromDIP(30)));
        SetCursor(wxCursor(wxCURSOR_HAND));
        Bind(wxEVT_PAINT, &PrintbenchCameraTile::on_paint, this);
        Bind(wxEVT_ENTER_WINDOW, [this](wxMouseEvent& e) { m_hover = true; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEAVE_WINDOW, [this](wxMouseEvent& e) { m_hover = false; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEFT_UP, [this](wxMouseEvent&) {
            if (!IsEnabled()) return;
            wxCommandEvent event(wxEVT_BUTTON, GetId());
            event.SetEventObject(this);
            ProcessWindowEvent(event);
        });
    }

    bool Enable(bool enable = true)
    {
        const bool changed = wxPanel::Enable(enable);
        SetCursor(wxCursor(enable ? wxCURSOR_HAND : wxCURSOR_ARROW));
        Refresh(false);
        return changed;
    }

    void SetCaption(const wxString& caption)
    {
        if (m_caption == caption) return;
        m_caption = caption;
        Refresh(false);
    }

    void SetAlert(bool alert)
    {
        if (m_alert == alert) return;
        m_alert = alert;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        wxColour fill = m_alert ? wxColour(92, 27, 42) : wxColour(8, 37, 55);
        if (!IsEnabled())
            fill = wxColour(18, 31, 40);
        else if (m_hover)
            fill = fill.ChangeLightness(115);
        const wxColour border = m_alert && IsEnabled() ? wxColour(180, 58, 78)
                                                       : (IsEnabled() ? wxColour(22, 91, 119) : PB_BORDER);
        dc.SetPen(wxPen(border, 1));
        dc.SetBrush(wxBrush(fill));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(5));

        wxFont font = GetFont();
        font.SetPointSize(8);
        font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(font);
        dc.SetTextForeground(IsEnabled() ? PB_TEXT : PB_MUTED);
        const wxSize ext = dc.GetTextExtent(m_caption);
        dc.DrawText(m_caption, std::max(FromDIP(4), (size.x - ext.x) / 2), std::max(FromDIP(3), (size.y - ext.y) / 2));
    }

    wxString m_caption;
    bool m_alert{false};
    bool m_hover{false};
};

class PrintbenchSpeedPill : public wxPanel
{
public:
    PrintbenchSpeedPill(wxWindow* parent, const wxString& caption)
        : wxPanel(parent, wxID_ANY), m_caption(caption)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(76), FromDIP(32)));
        SetCursor(wxCursor(wxCURSOR_HAND));
        Bind(wxEVT_PAINT, &PrintbenchSpeedPill::on_paint, this);
        Bind(wxEVT_ENTER_WINDOW, [this](wxMouseEvent& e) { m_hover = true; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEAVE_WINDOW, [this](wxMouseEvent& e) { m_hover = false; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEFT_UP, [this](wxMouseEvent&) {
            if (!IsEnabled()) return;
            wxCommandEvent event(wxEVT_BUTTON, GetId());
            event.SetEventObject(this);
            ProcessWindowEvent(event);
        });
    }

    bool Enable(bool enable = true)
    {
        const bool changed = wxPanel::Enable(enable);
        SetCursor(wxCursor(enable ? wxCURSOR_HAND : wxCURSOR_ARROW));
        Refresh(false);
        return changed;
    }

    void SetActive(bool active)
    {
        if (m_active == active) return;
        m_active = active;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        wxColour fill = m_active ? wxColour(10, 99, 216) : wxColour(8, 37, 55);
        if (!IsEnabled())
            fill = wxColour(18, 31, 40);
        else if (m_hover)
            fill = fill.ChangeLightness(115);
        const wxColour border = m_active && IsEnabled() ? wxColour(38, 142, 255) : PB_BORDER;
        dc.SetPen(wxPen(border, 1));
        dc.SetBrush(wxBrush(fill));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(6));

        wxFont font = GetFont();
        font.SetPointSize(8);
        font.SetWeight(m_active ? wxFONTWEIGHT_BOLD : wxFONTWEIGHT_NORMAL);
        dc.SetFont(font);
        dc.SetTextForeground(IsEnabled() ? *wxWHITE : PB_MUTED);
        const wxSize ext = dc.GetTextExtent(m_caption);
        dc.DrawText(m_caption, std::max(FromDIP(4), (size.x - ext.x) / 2), std::max(FromDIP(3), (size.y - ext.y) / 2));
    }

    wxString m_caption;
    bool m_active{false};
    bool m_hover{false};
};

class PrintbenchActionTile : public wxPanel
{
public:
    PrintbenchActionTile(wxWindow* parent, const wxString& caption, const wxBitmap& bitmap)
        : wxPanel(parent, wxID_ANY), m_caption(caption), m_bitmap(bitmap)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(118), FromDIP(46)));
        SetCursor(wxCursor(wxCURSOR_HAND));
        Bind(wxEVT_PAINT, &PrintbenchActionTile::on_paint, this);
        Bind(wxEVT_ENTER_WINDOW, [this](wxMouseEvent& e) { m_hover = true; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEAVE_WINDOW, [this](wxMouseEvent& e) { m_hover = false; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEFT_UP, [this](wxMouseEvent&) {
            if (!IsEnabled()) return;
            wxCommandEvent event(wxEVT_BUTTON, GetId());
            event.SetEventObject(this);
            ProcessWindowEvent(event);
        });
    }

    bool Enable(bool enable = true)
    {
        const bool changed = wxPanel::Enable(enable);
        SetCursor(wxCursor(enable ? wxCURSOR_HAND : wxCURSOR_ARROW));
        Refresh(false);
        return changed;
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        wxColour fill = IsEnabled() ? wxColour(8, 37, 55) : wxColour(17, 31, 41);
        if (IsEnabled() && m_hover)
            fill = wxColour(10, 50, 70);
        const wxColour border = IsEnabled() ? wxColour(20, 98, 126) : PB_BORDER;
        dc.SetPen(wxPen(border, 1));
        dc.SetBrush(wxBrush(fill));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(6));

        const int icon_size = FromDIP(16);
        const int icon_x = FromDIP(10);
        const int icon_y = std::max(0, (size.y - icon_size) / 2);
        if (m_bitmap.IsOk())
            dc.DrawBitmap(m_bitmap, icon_x, icon_y, true);

        wxFont font = GetFont();
        font.SetPointSize(9);
        font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(font);
        dc.SetTextForeground(IsEnabled() ? PB_TEXT : PB_MUTED);
        const int text_x = FromDIP(34);
        const wxSize ext = dc.GetTextExtent(m_caption);
        const int text_y = std::max(FromDIP(4), (size.y - ext.y) / 2);
        dc.DrawText(m_caption, text_x, text_y);
    }

    wxString m_caption;
    wxBitmap m_bitmap;
    bool m_hover{false};
};

class PrintbenchHistoryRow : public wxPanel
{
public:
    explicit PrintbenchHistoryRow(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(260), FromDIP(58)));
        Bind(wxEVT_PAINT, &PrintbenchHistoryRow::on_paint, this);
    }

    void clear()
    {
        m_visible = false;
        m_empty = false;
        Refresh(false);
    }

    void set_empty_state(const wxString& text)
    {
        m_visible = true;
        m_empty = true;
        m_name = text;
        m_finished.clear();
        m_duration.clear();
        m_status.clear();
        Refresh(false);
    }

    void set_entry(const wxString& name, const wxString& finished, const wxString& duration, const wxString& status)
    {
        m_visible = true;
        m_empty = false;
        m_name = name;
        m_finished = finished;
        m_duration = duration;
        m_status = status;
        Refresh(false);
    }

private:
    static wxString fit_text(wxDC& dc, wxString text, int max_width)
    {
        if (max_width <= 0)
            return wxEmptyString;
        if (dc.GetTextExtent(text).x <= max_width)
            return text;
        const wxString ellipsis = wxString::FromUTF8("…");
        while (!text.empty() && dc.GetTextExtent(text + ellipsis).x > max_width)
            text.RemoveLast();
        return text + ellipsis;
    }

    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (!m_visible || size.x < FromDIP(80) || size.y < FromDIP(30))
            return;

        dc.SetPen(wxPen(PB_BORDER, 1));
        dc.SetBrush(wxBrush(wxColour(8, 25, 37)));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(6));

        wxFont body_font = GetFont();
        body_font.SetPointSize(9);
        wxFont name_font = body_font;
        name_font.SetPointSize(10);
        name_font.SetWeight(wxFONTWEIGHT_BOLD);

        if (m_empty) {
            dc.SetFont(body_font);
            dc.SetTextForeground(PB_MUTED);
            dc.DrawText(m_name, FromDIP(12), std::max(FromDIP(8), (size.y - dc.GetTextExtent(m_name).y) / 2));
            return;
        }

        const int thumb_x = FromDIP(8);
        const int thumb_y = FromDIP(7);
        const int thumb = std::min(FromDIP(44), size.y - FromDIP(14));
        dc.SetPen(wxPen(wxColour(30, 72, 94), 1));
        dc.SetBrush(wxBrush(wxColour(6, 33, 50)));
        dc.DrawRoundedRectangle(thumb_x, thumb_y, thumb, thumb, FromDIP(5));
        dc.SetPen(wxPen(PB_ACCENT, std::max(1, FromDIP(2))));
        dc.SetBrush(*wxTRANSPARENT_BRUSH);
        const int cube = FromDIP(18);
        const int cx = thumb_x + thumb / 2;
        const int cy = thumb_y + thumb / 2;
        dc.DrawRectangle(cx - cube / 2, cy - cube / 2, cube, cube);
        dc.DrawLine(cx - cube / 2, cy - cube / 2, cx, cy - cube);
        dc.DrawLine(cx + cube / 2, cy - cube / 2, cx, cy - cube);
        dc.DrawLine(cx, cy - cube, cx, cy);

        wxString badge = m_status;
        badge.MakeUpper();
        if (badge.empty())
            badge = "STATUS";
        wxFont badge_font = body_font;
        badge_font.SetPointSize(8);
        badge_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(badge_font);
        const wxSize badge_ext = dc.GetTextExtent(badge);
        const int badge_w = badge_ext.x + FromDIP(16);
        const int badge_h = badge_ext.y + FromDIP(7);
        const int badge_x = size.x - badge_w - FromDIP(9);
        const int badge_y = FromDIP(9);
        const bool finished = m_status.CmpNoCase("Fertig") == 0;
        const wxColour badge_colour = finished ? wxColour(21, 92, 70) : wxColour(103, 70, 24);
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(badge_colour));
        dc.DrawRoundedRectangle(badge_x, badge_y, badge_w, badge_h, FromDIP(5));
        dc.SetTextForeground(finished ? wxColour(117, 239, 191) : wxColour(255, 204, 117));
        dc.DrawText(badge, badge_x + FromDIP(8), badge_y + FromDIP(3));

        const int text_x = thumb_x + thumb + FromDIP(10);
        const int text_right = badge_x - FromDIP(8);
        dc.SetFont(name_font);
        dc.SetTextForeground(PB_TEXT);
        dc.DrawText(fit_text(dc, m_name, text_right - text_x), text_x, FromDIP(8));

        dc.SetFont(body_font);
        dc.SetTextForeground(PB_MUTED);
        const wxString meta = m_finished + "  •  " + m_duration;
        dc.DrawText(fit_text(dc, meta, size.x - text_x - FromDIP(12)), text_x, FromDIP(31));
    }

    bool m_visible{false};
    bool m_empty{false};
    wxString m_name;
    wxString m_finished;
    wxString m_duration;
    wxString m_status;
};

class PrintbenchQuickTile : public wxPanel
{
public:
    enum class Kind { Print, Pause, Stop, Light };

    PrintbenchQuickTile(wxWindow* parent, Kind kind, const wxString& caption, const wxColour& colour)
        : wxPanel(parent, wxID_ANY), m_kind(kind), m_caption(caption), m_colour(colour)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(76), FromDIP(68)));
        SetCursor(wxCursor(wxCURSOR_HAND));
        Bind(wxEVT_PAINT, &PrintbenchQuickTile::on_paint, this);
        Bind(wxEVT_ENTER_WINDOW, [this](wxMouseEvent& e) { m_hover = true; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEAVE_WINDOW, [this](wxMouseEvent& e) { m_hover = false; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEFT_UP, [this](wxMouseEvent&) {
            if (!IsEnabled()) return;
            wxCommandEvent event(wxEVT_BUTTON, GetId());
            event.SetEventObject(this);
            ProcessWindowEvent(event);
        });
    }

    bool Enable(bool enable = true)
    {
        const bool changed = wxPanel::Enable(enable);
        Refresh(false);
        return changed;
    }

    void SetCaption(const wxString& caption)
    {
        if (m_caption == caption) return;
        m_caption = caption;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();

        wxColour fill = IsEnabled() ? m_colour : wxColour(25, 43, 55);
        if (IsEnabled() && m_hover)
            fill = fill.ChangeLightness(116);
        dc.SetPen(wxPen(IsEnabled() ? fill.ChangeLightness(132) : PB_BORDER, 1));
        dc.SetBrush(wxBrush(fill));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(7));

        const int cx = size.x / 2;
        const int cy = FromDIP(24);
        const wxColour icon = IsEnabled() ? *wxWHITE : PB_MUTED;
        dc.SetPen(wxPen(icon, std::max(1, FromDIP(2))));
        dc.SetBrush(wxBrush(icon));
        switch (m_kind) {
        case Kind::Print: {
            wxPoint pts[3]{{cx - FromDIP(6), cy - FromDIP(8)}, {cx - FromDIP(6), cy + FromDIP(8)}, {cx + FromDIP(8), cy}};
            dc.DrawPolygon(3, pts);
            break;
        }
        case Kind::Pause:
            dc.DrawRoundedRectangle(cx - FromDIP(8), cy - FromDIP(8), FromDIP(5), FromDIP(16), FromDIP(1));
            dc.DrawRoundedRectangle(cx + FromDIP(3), cy - FromDIP(8), FromDIP(5), FromDIP(16), FromDIP(1));
            break;
        case Kind::Stop:
            dc.DrawRoundedRectangle(cx - FromDIP(7), cy - FromDIP(7), FromDIP(14), FromDIP(14), FromDIP(2));
            break;
        case Kind::Light:
            dc.SetBrush(*wxTRANSPARENT_BRUSH);
            dc.DrawCircle(cx, cy - FromDIP(2), FromDIP(7));
            dc.DrawLine(cx - FromDIP(4), cy + FromDIP(6), cx + FromDIP(4), cy + FromDIP(6));
            dc.DrawLine(cx - FromDIP(3), cy + FromDIP(9), cx + FromDIP(3), cy + FromDIP(9));
            for (int dx : {-12, 0, 12})
                dc.DrawLine(cx + FromDIP(dx), cy - FromDIP(14), cx + FromDIP(dx == 0 ? 0 : (dx < 0 ? -9 : 9)), cy - FromDIP(11));
            break;
        }

        wxFont font = GetFont();
        font.SetPointSize(9);
        font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(font);
        dc.SetTextForeground(IsEnabled() ? *wxWHITE : PB_MUTED);
        const wxSize ext = dc.GetTextExtent(m_caption);
        dc.DrawText(m_caption, std::max(FromDIP(4), (size.x - ext.x) / 2), size.y - ext.y - FromDIP(8));
    }

    Kind m_kind;
    wxString m_caption;
    wxColour m_colour;
    bool m_hover{false};
};

class PrintbenchCardPanel : public wxPanel
{
public:
    explicit PrintbenchCardPanel(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        Bind(wxEVT_PAINT, &PrintbenchCardPanel::on_paint, this);
        Bind(wxEVT_SIZE, [this](wxSizeEvent& e) { Refresh(false); e.Skip(); });
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_BG));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;
        dc.SetPen(wxPen(wxColour(24, 59, 78), 1));
        dc.SetBrush(wxBrush(PB_CARD));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(8));
    }
};

class PrintbenchHeaderStatus : public wxPanel
{
public:
    explicit PrintbenchHeaderStatus(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(118), FromDIP(36)));
        Bind(wxEVT_PAINT, &PrintbenchHeaderStatus::on_paint, this);
    }

    void SetSnapshot(bool online, const wxString& wifi)
    {
        m_online = online;
        m_wifi = wifi;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_BG));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        const wxColour state_colour = m_online ? PB_OK : PB_MUTED;
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(state_colour));
        dc.DrawCircle(FromDIP(7), FromDIP(11), FromDIP(3));

        wxFont title_font = GetFont();
        title_font.SetPointSize(8);
        title_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(title_font);
        dc.SetTextForeground(m_online ? PB_TEXT : PB_MUTED);
        dc.DrawText(m_online ? "P2S Online" : "P2S Offline", FromDIP(15), FromDIP(3));

        wxFont meta_font = GetFont();
        meta_font.SetPointSize(7);
        dc.SetFont(meta_font);
        dc.SetTextForeground(PB_MUTED);
        const wxString meta = m_online
            ? (m_wifi.empty() ? wxString(L"LAN \u2022 lokal") : wxString(L"LAN \u2022 ") + m_wifi)
            : wxString("Keine LAN-Verbindung");
        dc.DrawText(meta, FromDIP(15), FromDIP(19));
    }

    bool m_online{false};
    wxString m_wifi;
};

class PrintbenchTopNavItem : public wxPanel
{
public:
    PrintbenchTopNavItem(wxWindow* parent, const wxString& caption, const wxBitmap& bitmap)
        : wxPanel(parent, wxID_ANY), m_caption(caption), m_bitmap(bitmap)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(92), FromDIP(42)));
        SetCursor(wxCursor(wxCURSOR_HAND));
        Bind(wxEVT_PAINT, &PrintbenchTopNavItem::on_paint, this);
        Bind(wxEVT_ENTER_WINDOW, [this](wxMouseEvent& e) { m_hover = true; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEAVE_WINDOW, [this](wxMouseEvent& e) { m_hover = false; Refresh(false); e.Skip(); });
    }

    void SetActive(bool active)
    {
        if (m_active == active) return;
        m_active = active;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_BG));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        if (m_active || m_hover) {
            dc.SetPen(*wxTRANSPARENT_PEN);
            dc.SetBrush(wxBrush(m_active ? wxColour(5, 46, 103) : wxColour(5, 24, 40)));
            dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(7));
        }
        if (m_active) {
            dc.SetPen(*wxTRANSPARENT_PEN);
            dc.SetBrush(wxBrush(PB_ACCENT));
            dc.DrawRoundedRectangle(FromDIP(6), size.y - FromDIP(2), size.x - FromDIP(12), FromDIP(2), FromDIP(1));
        }

        const int icon_size = FromDIP(16);
        const int icon_x = FromDIP(8);
        const int icon_y = std::max(0, (size.y - icon_size) / 2);
        if (m_bitmap.IsOk())
            dc.DrawBitmap(m_bitmap, icon_x, icon_y, true);

        wxFont font = GetFont();
        font.SetPointSize(9);
        font.SetWeight(m_active ? wxFONTWEIGHT_BOLD : wxFONTWEIGHT_NORMAL);
        dc.SetFont(font);
        dc.SetTextForeground(m_active ? *wxWHITE : wxColour(181, 199, 213));
        const wxSize ext = dc.GetTextExtent(m_caption);
        dc.DrawText(m_caption, FromDIP(31), std::max(FromDIP(4), (size.y - ext.y) / 2));
    }

    wxString m_caption;
    wxBitmap m_bitmap;
    bool m_active{false};
    bool m_hover{false};
};

class PrintbenchNavRow : public wxPanel
{
public:
    PrintbenchNavRow(wxWindow* parent, const wxString& caption, const wxBitmap& bitmap)
        : wxPanel(parent, wxID_ANY), m_caption(caption), m_bitmap(bitmap)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(-1, FromDIP(42)));
        SetCursor(wxCursor(wxCURSOR_HAND));
        Bind(wxEVT_PAINT, &PrintbenchNavRow::on_paint, this);
        Bind(wxEVT_ENTER_WINDOW, [this](wxMouseEvent& e) { m_hover = true; Refresh(false); e.Skip(); });
        Bind(wxEVT_LEAVE_WINDOW, [this](wxMouseEvent& e) { m_hover = false; Refresh(false); e.Skip(); });
    }

    void SetActive(bool active)
    {
        if (m_active == active) return;
        m_active = active;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(wxColour(2, 11, 22)));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        wxColour fill = wxColour(2, 11, 22);
        if (m_active)
            fill = wxColour(13, 112, 238);
        else if (m_hover)
            fill = wxColour(6, 29, 48);
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(fill));
        if (m_active || m_hover)
            dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(8));
        if (m_active) {
            dc.SetBrush(wxBrush(PB_ACCENT));
            dc.DrawRoundedRectangle(FromDIP(5), size.y - FromDIP(3), size.x - FromDIP(10), FromDIP(3), FromDIP(2));
        }

        const int icon_size = FromDIP(18);
        const int icon_x = FromDIP(13);
        const int icon_y = std::max(0, (size.y - icon_size) / 2);
        if (m_bitmap.IsOk())
            dc.DrawBitmap(m_bitmap, icon_x, icon_y, true);

        wxFont font = GetFont();
        font.SetPointSize(9);
        font.SetWeight(m_active ? wxFONTWEIGHT_BOLD : wxFONTWEIGHT_NORMAL);
        dc.SetFont(font);
        dc.SetTextForeground(m_active ? *wxWHITE : wxColour(184, 201, 214));
        const wxSize ext = dc.GetTextExtent(m_caption);
        dc.DrawText(m_caption, FromDIP(42), std::max(FromDIP(4), (size.y - ext.y) / 2));
    }

    wxString m_caption;
    wxBitmap m_bitmap;
    bool m_active{false};
    bool m_hover{false};
};

class PrintbenchAmsEnvironmentBar : public wxPanel
{
public:
    explicit PrintbenchAmsEnvironmentBar(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(-1, FromDIP(32)));
        Bind(wxEVT_PAINT, &PrintbenchAmsEnvironmentBar::on_paint, this);
    }

    void SetEnvironment(bool connected, float temp_c, int humidity)
    {
        m_connected = connected;
        m_temp_c = temp_c;
        m_humidity = humidity;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;
        dc.SetPen(wxPen(wxColour(23, 56, 74), 1));
        dc.SetBrush(wxBrush(wxColour(8, 25, 37)));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(5));

        wxFont label_font = GetFont();
        label_font.SetPointSize(8);
        label_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(label_font);
        dc.SetTextForeground(PB_MUTED);
        dc.DrawText("AMS ENV", FromDIP(9), FromDIP(8));

        wxFont value_font = GetFont();
        value_font.SetPointSize(9);
        value_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(value_font);
        const wxString value = m_connected
            ? wxString::Format("%.1f °C     %d %% RH", m_temp_c, m_humidity)
            : wxString("NICHT VERBUNDEN");
        dc.SetTextForeground(m_connected ? PB_OK : PB_MUTED);
        const wxSize ext = dc.GetTextExtent(value);
        dc.DrawText(value, std::max(FromDIP(72), size.x - ext.x - FromDIP(9)), FromDIP(7));
    }

    bool m_connected{false};
    float m_temp_c{0.0f};
    int m_humidity{-1};
};

class PrintbenchStatusRowPanel : public wxPanel
{
public:
    explicit PrintbenchStatusRowPanel(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        Bind(wxEVT_PAINT, &PrintbenchStatusRowPanel::on_paint, this);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;
        dc.SetPen(wxPen(wxColour(23, 56, 74), 1));
        dc.SetBrush(wxBrush(wxColour(8, 25, 37)));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(5));
    }
};

class PrintbenchDeviceStatusCell : public wxPanel
{
public:
    PrintbenchDeviceStatusCell(wxWindow* parent, const wxString& caption)
        : wxPanel(parent, wxID_ANY), m_caption(caption)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(FromDIP(115), FromDIP(54)));
        Bind(wxEVT_PAINT, &PrintbenchDeviceStatusCell::on_paint, this);
    }

    void SetState(const wxString& value, bool ok)
    {
        m_value = value;
        m_ok = ok;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        dc.SetPen(wxPen(wxColour(24, 58, 76), 1));
        dc.SetBrush(wxBrush(wxColour(8, 25, 37)));
        dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(6));

        wxFont caption_font = GetFont();
        caption_font.SetPointSize(8);
        caption_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(caption_font);
        dc.SetTextForeground(PB_MUTED);
        dc.DrawText(m_caption, FromDIP(10), FromDIP(7));

        const wxColour state_colour = m_ok ? PB_OK : PB_MUTED;
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(state_colour));
        dc.DrawCircle(FromDIP(13), FromDIP(35), FromDIP(3));

        wxFont value_font = GetFont();
        value_font.SetPointSize(10);
        value_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(value_font);
        dc.SetTextForeground(m_ok ? PB_TEXT : PB_MUTED);
        dc.DrawText(m_value, FromDIP(22), FromDIP(27));
    }

    wxString m_caption;
    wxString m_value{"--"};
    bool m_ok{false};
};

class PrintbenchSidebarDevice : public wxPanel
{
public:
    PrintbenchSidebarDevice(wxWindow* parent, const wxString& name, const wxBitmap& bitmap)
        : wxPanel(parent, wxID_ANY), m_name(name), m_bitmap(bitmap)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(-1, FromDIP(44)));
        Bind(wxEVT_PAINT, &PrintbenchSidebarDevice::on_paint, this);
    }

    void SetState(bool online, const wxString& state)
    {
        m_online = online;
        m_state = state;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(wxColour(4, 14, 24)));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        if (m_bitmap.IsOk())
            dc.DrawBitmap(m_bitmap, FromDIP(7), std::max(0, (size.y - FromDIP(18)) / 2), true);

        wxFont name_font = GetFont();
        name_font.SetPointSize(8);
        name_font.SetWeight(wxFONTWEIGHT_BOLD);
        dc.SetFont(name_font);
        dc.SetTextForeground(PB_TEXT);
        dc.DrawText(m_name, FromDIP(33), FromDIP(5));

        const wxColour state_colour = m_online ? PB_OK : PB_MUTED;
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(state_colour));
        dc.DrawCircle(FromDIP(37), FromDIP(29), FromDIP(3));
        wxFont state_font = GetFont();
        state_font.SetPointSize(8);
        dc.SetFont(state_font);
        dc.SetTextForeground(state_colour);
        dc.DrawText(m_state, FromDIP(45), FromDIP(21));
    }

    wxString m_name;
    wxString m_state{"Offline"};
    wxBitmap m_bitmap;
    bool m_online{false};
};

class PrintbenchProgressBar : public wxPanel
{
public:
    explicit PrintbenchProgressBar(wxWindow* parent)
        : wxPanel(parent, wxID_ANY)
    {
        SetBackgroundStyle(wxBG_STYLE_PAINT);
        SetMinSize(wxSize(-1, FromDIP(10)));
        Bind(wxEVT_PAINT, &PrintbenchProgressBar::on_paint, this);
    }

    void SetValue(int value)
    {
        const int next = std::clamp(value, 0, 100);
        if (next == m_value)
            return;
        m_value = next;
        Refresh(false);
    }

private:
    void on_paint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        const wxSize size = GetClientSize();
        dc.SetBackground(wxBrush(PB_CARD));
        dc.Clear();
        if (size.x <= 0 || size.y <= 0)
            return;

        const int radius = std::max(1, FromDIP(3));
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(wxBrush(PB_BORDER));
        dc.DrawRoundedRectangle(0, 0, size.x, size.y, radius);
        if (m_value <= 0)
            return;

        const int fill_width = std::max(FromDIP(3), (size.x * m_value) / 100);
        dc.SetBrush(wxBrush(PB_ACCENT));
        dc.DrawRoundedRectangle(0, 0, fill_width, size.y, radius);
    }

    int m_value{0};
};

PrintbenchNativePanel::PrintbenchNativePanel(wxWindow* parent)
    : wxScrolledWindow(parent, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxVSCROLL | wxTAB_TRAVERSAL)
{
    SetBackgroundColour(PB_BG);
    SetScrollRate(0, FromDIP(12));

    auto* shell = new wxBoxSizer(wxHORIZONTAL);
    // FINAL-MASTER fills the available desktop viewport edge-to-edge.

    // Keep all fourteen master navigation rows and the connected-device cards
    // reachable on shorter Windows desktops, without scrolling the dashboard.
    auto* sidebar = new wxScrolledWindow(this, wxID_ANY, wxDefaultPosition,
                                         wxDefaultSize, wxVSCROLL | wxTAB_TRAVERSAL);
    sidebar->SetScrollRate(0, FromDIP(12));
    sidebar->SetBackgroundColour(wxColour(2, 11, 22));
    sidebar->SetMinSize(wxSize(FromDIP(208), -1));
    auto* side = new wxBoxSizer(wxVERTICAL);
    auto* brand_row = new wxBoxSizer(wxHORIZONTAL);
    auto brand_icon_bitmap = create_scaled_bitmap("printbench_app_icon_32", sidebar, 30);
    auto* brand_icon = new wxStaticBitmap(sidebar, wxID_ANY, brand_icon_bitmap);
    auto* brand_text = new wxBoxSizer(wxVERTICAL);
    auto* brand = new wxStaticText(sidebar, wxID_ANY, "PRINTBENCH");
    style_label(brand, 17, true);
    auto* brand_sub = new wxStaticText(sidebar, wxID_ANY, wxString(L"Studio  \u2022  JL1976 Software"));
    style_label(brand_sub, 8, false, PB_MUTED);
    brand_text->Add(brand, 0);
    brand_text->Add(brand_sub, 0, wxTOP, FromDIP(1));
    brand_row->Add(brand_icon, 0, wxRIGHT | wxALIGN_CENTER_VERTICAL, FromDIP(7));
    brand_row->Add(brand_text, 1, wxALIGN_CENTER_VERTICAL);
    side->Add(brand_row, 0, wxEXPAND | wxLEFT | wxRIGHT | wxTOP | wxBOTTOM, FromDIP(10));
    auto* brand_rule = new wxPanel(sidebar, wxID_ANY);
    brand_rule->SetBackgroundColour(wxColour(19, 47, 64));
    brand_rule->SetMinSize(wxSize(-1, FromDIP(1)));
    side->Add(brand_rule, 0, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, FromDIP(9));
    const std::array<wxString, 14> nav_items{
        wxString(L"\u00DCbersicht"), L"Live Ansicht", L"Steuerung", L"AMS 2 Pro", L"Material",
        wxString(L"Druckauftr\u00E4ge"), L"Historie", L"Dateien", L"Kamera", wxString(L"Ger\u00E4te-Setup"),
        L"Netzwerk", L"Sicherheit", L"Diagnose", L"System"};
    // Reuse Orca's native vector resources so the FINAL-MASTER rail stays crisp
    // at every Windows scaling level instead of falling back to text glyphs.
    const std::array<const char*, 14> nav_icons{
        "monitor", "monitor_camera", "monitor_axis_home_icon", "ams_setting_normal", "filament",
        "print_control_resume", "print_info_time", "topbar_file", "camera_setting", "printer",
        "printer_in_lan", "info", "calib_sf", "settings"};
    for (size_t i = 0; i < nav_items.size(); ++i) {
        auto icon_bitmap = create_scaled_bitmap(nav_icons[i], sidebar, 18);
        auto* item = new PrintbenchNavRow(sidebar, nav_items[i], icon_bitmap);
        item->SetActive(i == 0);
        m_nav_rows[i] = item;
        item->Bind(wxEVT_LEFT_UP, [this, i](wxMouseEvent&) { handle_nav(i); });
        side->Add(item, 0, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, FromDIP(2));
    }
    side->AddStretchSpacer();
    auto* device_caption = new wxStaticText(sidebar, wxID_ANY, "GERÄTE");
    style_label(device_caption, 7, true, PB_MUTED);
    side->Add(device_caption, 0, wxLEFT | wxRIGHT | wxBOTTOM, FromDIP(7));
    m_sidebar_devices[0] = new PrintbenchSidebarDevice(
        sidebar, "Bambu Lab P2S", create_scaled_bitmap("printer", sidebar, 18));
    m_sidebar_devices[1] = new PrintbenchSidebarDevice(
        sidebar, "AMS 2 Pro", create_scaled_bitmap("ams_setting_normal", sidebar, 18));
    side->Add(m_sidebar_devices[0], 0, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, FromDIP(6));
    side->Add(m_sidebar_devices[1], 0, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, FromDIP(9));
    sidebar->SetSizer(side);
    shell->Add(sidebar, 0, wxEXPAND);

    auto* root = new wxBoxSizer(wxVERTICAL);
    auto* header = new wxBoxSizer(wxHORIZONTAL);
    // FINAL MASTER: no duplicate top navigation. The header is status-only.
    header->AddStretchSpacer();
    m_header_status = new PrintbenchHeaderStatus(this);
    header->Add(m_header_status, 0, wxLEFT | wxRIGHT | wxALIGN_CENTER_VERTICAL, FromDIP(8));
    root->Add(header, 0, wxEXPAND | wxLEFT | wxRIGHT | wxTOP, FromDIP(10));
    root->AddSpacer(FromDIP(4));

    auto* hero = new wxBoxSizer(wxHORIZONTAL);
    wxBoxSizer* body = nullptr;

    auto* printer_card = new PrintbenchCardPanel(this);
    m_printer_card = printer_card;
    printer_card->SetMinSize(wxSize(FromDIP(390), FromDIP(400)));
    auto* printer_body = new wxBoxSizer(wxVERTICAL);
    auto hero_bitmap = create_scaled_bitmap("printbench_hero_p2s_ams", this, 560);
    m_hero_panel = new PrintbenchHeroPanel(printer_card, hero_bitmap);
    printer_body->Add(m_hero_panel, 1, wxEXPAND | wxALL, FromDIP(6));
    printer_card->SetSizer(printer_body);
    hero->Add(printer_card, 42, wxEXPAND | wxRIGHT, FromDIP(8));

    auto* status_card = make_card(this, "DRUCKERSTATUS", body);
    auto add_status_section = [&](const wxString& caption) {
        auto* label = new wxStaticText(status_card, wxID_ANY, caption);
        style_label(label, 8, true, PB_MUTED);
        body->Add(label, 0, wxLEFT | wxRIGHT | wxTOP | wxBOTTOM, FromDIP(4));
    };
    m_status_ready = add_status_value(status_card, body, "Status", m_printer_status_dots[0]);
    add_status_section("AKTUELLE TEMPERATUR");
    m_nozzle = add_status_value(status_card, body, wxString(L"D\u00FCse"), m_printer_status_dots[1]);
    m_bed = add_status_value(status_card, body, "Druckbett", m_printer_status_dots[2]);
    m_chamber = add_status_value(status_card, body, "Kammer", m_printer_status_dots[3]);
    add_status_section("GESCHWINDIGKEIT");
    m_speed = add_status_value(status_card, body, "Modus", m_printer_status_dots[4]);
    add_status_section("AMS 2 PRO");
    m_ams_summary = add_status_value(status_card, body, "Status", m_printer_status_dots[5]);
    status_card->SetMinSize(wxSize(FromDIP(230), FromDIP(400)));
    hero->Add(status_card, 24, wxEXPAND | wxRIGHT, FromDIP(8));

    auto* right_hero = new wxBoxSizer(wxVERTICAL);
    auto* camera_card = make_card(this, "LIVE KAMERA", body);
    m_camera_card = camera_card;
    // Video, player chrome and camera action row must fit without overlap.
    camera_card->SetMinSize(wxSize(FromDIP(330), FromDIP(280)));
    m_camera = add_value(camera_card, body, "Kamera");
    m_media_ctrl = new wxMediaCtrl2(camera_card);
    m_media_ctrl->SetMinSize(wxSize(FromDIP(330), FromDIP(155)));
    m_media_ctrl->SetBackgroundColour(*wxBLACK);
    m_media_play_ctrl = new MediaPlayCtrl(camera_card, m_media_ctrl, wxDefaultPosition, wxSize(-1, FromDIP(34)));
    m_media_play_ctrl->SetBackgroundColour(PB_CARD);
    body->Add(m_media_ctrl, 1, wxEXPAND | wxTOP, FromDIP(6));
    body->Add(m_media_play_ctrl, 0, wxEXPAND | wxTOP, FromDIP(4));

    auto* camera_actions = new wxBoxSizer(wxHORIZONTAL);
    m_camera_record = new PrintbenchCameraTile(camera_card, ID_PB_CAMERA_RECORD, "AUFNAHME");
    m_camera_timelapse = new PrintbenchCameraTile(camera_card, ID_PB_CAMERA_TIMELAPSE, "TIMELAPSE");
    m_camera_resolution = new PrintbenchCameraTile(camera_card, ID_PB_CAMERA_RESOLUTION, wxString::FromUTF8("AUFLÖSUNG"));
    for (auto* button : {m_camera_record, m_camera_timelapse, m_camera_resolution}) {
        button->Enable(false);
        camera_actions->Add(button, 1, button == m_camera_resolution ? 0 : wxRIGHT, FromDIP(5));
    }
    Bind(wxEVT_BUTTON, &PrintbenchNativePanel::on_camera_action, this, ID_PB_CAMERA_RECORD);
    Bind(wxEVT_BUTTON, &PrintbenchNativePanel::on_camera_action, this, ID_PB_CAMERA_TIMELAPSE);
    Bind(wxEVT_BUTTON, &PrintbenchNativePanel::on_camera_action, this, ID_PB_CAMERA_RESOLUTION);
    body->Add(camera_actions, 0, wxEXPAND | wxTOP, FromDIP(5));
    right_hero->Add(camera_card, 1, wxEXPAND | wxBOTTOM, FromDIP(8));

    auto* quick_card = make_card(this, "SCHNELLSTEUERUNG", body);
    m_quick_card = quick_card;
    auto* controls = new wxBoxSizer(wxHORIZONTAL);
    m_print = new PrintbenchQuickTile(quick_card, PrintbenchQuickTile::Kind::Print, "DRUCKEN", wxColour("#075C46"));
    m_pause_resume = new PrintbenchQuickTile(quick_card, PrintbenchQuickTile::Kind::Pause, "PAUSE", wxColour("#6A4512"));
    m_stop = new PrintbenchQuickTile(quick_card, PrintbenchQuickTile::Kind::Stop, "STOP", wxColour("#651B2A"));
    m_light = new PrintbenchQuickTile(quick_card, PrintbenchQuickTile::Kind::Light, "LICHT", wxColour("#0A4C92"));
    m_pause_resume->Enable(false);
    m_stop->Enable(false);
    m_light->Enable(false);
    controls->Add(m_print, 1, wxRIGHT, FromDIP(7));
    controls->Add(m_pause_resume, 1, wxRIGHT, FromDIP(7));
    controls->Add(m_stop, 1, wxRIGHT, FromDIP(7));
    controls->Add(m_light, 1);
    body->Add(controls, 0, wxEXPAND | wxBOTTOM, FromDIP(10));
    auto* speed_modes = new wxBoxSizer(wxHORIZONTAL);
    const std::array<wxString, 4> speed_names{L"Leise", L"Standard", L"Sport", L"Ludicrous"};
    for (size_t i = 0; i < m_speed_buttons.size(); ++i) {
        m_speed_buttons[i] = new PrintbenchSpeedPill(quick_card, speed_names[i]);
        m_speed_buttons[i]->Enable(false);
        const auto level = static_cast<DevPrintingSpeedLevel>(static_cast<int>(i) + 1);
        m_speed_buttons[i]->Bind(wxEVT_BUTTON, [this, level](wxCommandEvent&) {
            if (m_machine != nullptr && m_machine->is_connected())
                m_machine->command_set_printing_speed(level);
        });
        speed_modes->Add(m_speed_buttons[i], 1, i + 1 < m_speed_buttons.size() ? wxRIGHT : 0, FromDIP(6));
    }
    body->Add(speed_modes, 0, wxEXPAND);
    right_hero->Add(quick_card, 0, wxEXPAND);
    hero->Add(right_hero, 34, wxEXPAND);

    root->Add(hero, 10, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(12));
    root->AddSpacer(FromDIP(8));

    auto* middle = new wxBoxSizer(wxHORIZONTAL);
    auto* print_card = make_card(this, "AKTUELLER DRUCK", body);
    m_print_card = print_card;
    m_job_header = new PrintbenchJobHeader(print_card);
    body->Add(m_job_header, 0, wxEXPAND | wxBOTTOM, FromDIP(10));

    m_progress_gauge = new PrintbenchProgressBar(print_card);
    body->Add(m_progress_gauge, 0, wxEXPAND | wxBOTTOM, FromDIP(10));

    auto* print_metrics = new wxBoxSizer(wxHORIZONTAL);
    auto add_metric = [&](const wxString& caption, wxStaticText*& value) {
        auto* col = new wxBoxSizer(wxVERTICAL);
        auto* name = new wxStaticText(print_card, wxID_ANY, caption);
        style_label(name, 9, true, PB_MUTED);
        value = new wxStaticText(print_card, wxID_ANY, "--");
        style_label(value, 13, true, PB_TEXT);
        col->Add(name, 0, wxBOTTOM, FromDIP(2));
        col->Add(value, 0);
        print_metrics->Add(col, 1, wxRIGHT, FromDIP(8));
    };
    add_metric("FORTSCHRITT", m_progress);
    add_metric("SCHICHTEN", m_layers);
    add_metric("RESTZEIT", m_remaining);
    body->Add(print_metrics, 0, wxEXPAND);
    middle->Add(print_card, 31, wxEXPAND | wxRIGHT, FromDIP(8));

    auto* temp_card = make_card(this, "TEMPERATUREN (LIVE)", body);
    temp_card->SetMinSize(wxSize(FromDIP(280), FromDIP(190)));
    auto* temp_values = new wxBoxSizer(wxHORIZONTAL);
    const std::array<wxString, 3> temp_names{L"D\u00DCSE", L"BETT", L"KAMMER"};
    const std::array<wxColour, 3> temp_colours{PB_ACCENT, wxColour(210,222,231), wxColour(90,145,165)};
    for (size_t i = 0; i < m_temp_values.size(); ++i) {
        auto* col = new wxBoxSizer(wxVERTICAL);
        auto* name = new wxStaticText(temp_card, wxID_ANY, temp_names[i]);
        style_label(name, 9, true, temp_colours[i]);
        m_temp_values[i] = new wxStaticText(temp_card, wxID_ANY, "-- C");
        style_label(m_temp_values[i], 13, true);
        col->Add(name, 0, wxBOTTOM, FromDIP(2));
        col->Add(m_temp_values[i], 0);
        temp_values->Add(col, 1, wxRIGHT, i + 1 < m_temp_values.size() ? FromDIP(10) : 0);
    }
    body->Add(temp_values, 0, wxEXPAND | wxBOTTOM, FromDIP(8));
    m_temp_chart = new PrintbenchTempChart(temp_card);
    body->Add(m_temp_chart, 1, wxEXPAND | wxTOP, FromDIP(4));
    middle->Add(temp_card, 35, wxEXPAND | wxRIGHT, FromDIP(8));

    auto* ams_card = make_card(this, "AMS 2 PRO", body);
    m_ams_card = ams_card;
    ams_card->SetMinSize(wxSize(FromDIP(300), FromDIP(190)));
    m_ams_environment = new PrintbenchAmsEnvironmentBar(ams_card);
    body->Add(m_ams_environment, 0, wxEXPAND | wxBOTTOM, FromDIP(7));
    auto* slot_grid = new wxFlexGridSizer(1, 4, FromDIP(8), FromDIP(8));
    for (int col = 0; col < 4; ++col)
        slot_grid->AddGrowableCol(col, 1);
    for (size_t i = 0; i < m_ams_slots.size(); ++i) {
        m_ams_slots[i] = new PrintbenchAmsSlotCard(ams_card, static_cast<int>(i + 1));
        slot_grid->Add(m_ams_slots[i], 1, wxEXPAND);
    }
    body->Add(slot_grid, 0, wxEXPAND | wxTOP, FromDIP(10));
    middle->Add(ams_card, 34, wxEXPAND);

    root->Add(middle, 6, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(12));
    root->AddSpacer(FromDIP(6));

    auto* bottom = new wxBoxSizer(wxHORIZONTAL);
    auto* device_card = make_card(this, wxString::FromUTF8("GERÄTESTATUS"), body);
    auto* device_grid = new wxFlexGridSizer(2, 3, FromDIP(8), FromDIP(8));
    for (int col = 0; col < 3; ++col)
        device_grid->AddGrowableCol(col, 1);
    const std::array<wxString, 6> status_names{
        L"P2S", L"KAMERA", L"AMS 2 PRO", L"WLAN", L"LOKALBETRIEB", L"CLOUD"};
    for (size_t i = 0; i < status_names.size(); ++i) {
        m_device_status_cells[i] = new PrintbenchDeviceStatusCell(device_card, status_names[i]);
        const bool initial_ok = i >= 4;
        const wxString initial_value = i == 4 ? L"Aktiv" : (i == 5 ? L"Nicht erforderlich" : L"--");
        m_device_status_cells[i]->SetState(initial_value, initial_ok);
        device_grid->Add(m_device_status_cells[i], 1, wxEXPAND);
    }
    body->Add(device_grid, 0, wxEXPAND | wxTOP, FromDIP(4));
    bottom->Add(device_card, 1, wxEXPAND | wxRIGHT, FromDIP(8));

    auto* history_card = make_card(this, "LETZTE DRUCKE", body);
    m_history_card = history_card;
    for (size_t i = 0; i < m_history_rows.size(); ++i) {
        m_history_rows[i] = new PrintbenchHistoryRow(history_card);
        if (i == 0)
            m_history_rows[i]->set_empty_state(wxString::FromUTF8("Noch keine lokalen Druckabschlüsse."));
        else
            m_history_rows[i]->clear();
        body->Add(m_history_rows[i], 0, wxEXPAND | wxBOTTOM, FromDIP(6));
    }
    bottom->Add(history_card, 1, wxEXPAND | wxRIGHT, FromDIP(8));

    auto* action_card = make_card(this, "SYSTEM & AKTIONEN", body);
    m_action_card = action_card;
    auto* action_grid = new wxFlexGridSizer(2, 3, FromDIP(6), FromDIP(6));
    for (int col = 0; col < 3; ++col)
        action_grid->AddGrowableCol(col, 1);
    const std::array<wxString, 6> action_names{
        L"Datei senden", L"Kalibrieren", L"Neustart", L"AMS trocknen", L"Firmware", L"Logs anzeigen"};
    const std::array<const char*, 6> action_icons{
        "topbar_file", "calib_sf", "refresh", "ams_setting_normal", "printer_sync", "info"};
    std::array<PrintbenchActionTile*, 6> action_buttons{};
    for (size_t i = 0; i < action_buttons.size(); ++i) {
        action_buttons[i] = new PrintbenchActionTile(
            action_card, action_names[i], create_scaled_bitmap(action_icons[i], action_card, 16));
        action_grid->Add(action_buttons[i], 1, wxEXPAND);
    }
    action_buttons[0]->Bind(wxEVT_BUTTON, [](wxCommandEvent&) {
        if (wxGetApp().mainframe)
            wxGetApp().mainframe->select_tab(MainFrame::tp3DEditor);
    });
    action_buttons[1]->Bind(wxEVT_BUTTON, [](wxCommandEvent&) {
        if (wxGetApp().mainframe)
            wxGetApp().mainframe->select_tab(MainFrame::tpCalibration);
    });
    action_buttons[5]->Bind(wxEVT_BUTTON, [](wxCommandEvent&) {
        if (wxGetApp().mainframe)
            wxGetApp().mainframe->show_log_window();
    });
    action_buttons[2]->Enable(false);
    action_buttons[2]->SetToolTip("Kein verifizierter P2S-Neustartbefehl im aktuellen LAN-Pfad");
    action_buttons[3]->Enable(false);
    action_buttons[3]->SetToolTip(wxString::FromUTF8("AMS-Trocknen benötigt Material-, Temperatur- und Zeitparameter"));
    action_buttons[4]->Enable(false);
    action_buttons[4]->SetToolTip("Firmware-Verwaltung wird erst nach verifiziertem P2S-Updatepfad aktiviert");
    body->Add(action_grid, 0, wxEXPAND | wxTOP, FromDIP(4));
    bottom->Add(action_card, 1, wxEXPAND);

    m_print->Bind(wxEVT_BUTTON, [this](wxCommandEvent&) {
        if (wxGetApp().mainframe)
            wxGetApp().mainframe->select_tab(MainFrame::tp3DEditor);
    });
    m_pause_resume->Bind(wxEVT_BUTTON, [this](wxCommandEvent&) {
        if (m_machine == nullptr || !m_machine->is_connected())
            return;
        if (m_machine->print_status == "PAUSE")
            m_machine->command_task_resume();
        else if (m_machine->print_status == "RUNNING")
            m_machine->command_task_pause();
    });
    m_stop->Bind(wxEVT_BUTTON, [this](wxCommandEvent&) {
        if (m_machine == nullptr || !m_machine->is_connected())
            return;
        if (wxMessageBox("Aktuellen Druck wirklich stoppen?", "PRINTBENCH", wxYES_NO | wxICON_WARNING, this) == wxYES)
            m_machine->command_task_abort();
    });
    m_light->Bind(wxEVT_BUTTON, [this](wxCommandEvent&) {
        if (m_machine == nullptr || !m_machine->is_connected() || m_machine->GetLamp() == nullptr)
            return;
        auto* lamp = m_machine->GetLamp();
        lamp->CtrlSetChamberLight(lamp->IsChamberLightOn() ? DevLamp::LIGHT_EFFECT_OFF : DevLamp::LIGHT_EFFECT_ON);
    });

    root->Add(bottom, 5, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, FromDIP(10));
    shell->Add(root, 1, wxEXPAND);
    SetSizer(shell);
    load_history();
    update_history_ui();
    Layout();
}

wxPanel* PrintbenchNativePanel::make_card(wxWindow* parent, const wxString& title, wxBoxSizer*& body)
{
    auto* card = new PrintbenchCardPanel(parent);
    auto* outer = new wxBoxSizer(wxVERTICAL);
    auto* heading = new wxStaticText(card, wxID_ANY, title);
    style_label(heading, 10, true, PB_ACCENT);
    outer->Add(heading, 0, wxLEFT | wxRIGHT | wxTOP | wxBOTTOM, FromDIP(6));
    auto* line = new wxStaticLine(card, wxID_ANY);
    line->SetForegroundColour(wxColour(20, 50, 67));
    outer->Add(line, 0, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(6));
    body = new wxBoxSizer(wxVERTICAL);
    outer->Add(body, 1, wxEXPAND | wxALL, FromDIP(6));
    card->SetSizer(outer);
    card->SetMinSize(wxSize(FromDIP(170), FromDIP(112)));
    return card;
}

wxStaticText* PrintbenchNativePanel::add_value(wxWindow* parent, wxSizer* sizer, const wxString& caption)
{
    auto* row = new wxBoxSizer(wxHORIZONTAL);
    auto* name = new wxStaticText(parent, wxID_ANY, caption);
    style_label(name, 11, false, PB_MUTED);
    auto* value = new wxStaticText(parent, wxID_ANY, "--");
    style_label(value, 13, true);
    row->Add(name, 1, wxALIGN_CENTER_VERTICAL);
    row->Add(value, 0, wxALIGN_CENTER_VERTICAL);
    sizer->Add(row, 0, wxEXPAND | wxBOTTOM, FromDIP(6));
    return value;
}

wxStaticText* PrintbenchNativePanel::add_status_value(wxWindow* parent, wxSizer* sizer, const wxString& caption, wxStaticText*& dot)
{
    auto* row_panel = new PrintbenchStatusRowPanel(parent);
    auto* row = new wxBoxSizer(wxHORIZONTAL);
    dot = new wxStaticText(row_panel, wxID_ANY, wxString(L"\u25CF"));
    style_label(dot, 9, true, PB_MUTED);
    auto* name = new wxStaticText(row_panel, wxID_ANY, caption);
    style_label(name, 10, false, PB_MUTED);
    auto* value = new wxStaticText(row_panel, wxID_ANY, "--");
    style_label(value, 11, true, PB_TEXT);
    row->Add(dot, 0, wxLEFT | wxRIGHT | wxALIGN_CENTER_VERTICAL, FromDIP(7));
    row->Add(name, 1, wxALIGN_CENTER_VERTICAL);
    row->Add(value, 0, wxRIGHT | wxALIGN_CENTER_VERTICAL, FromDIP(7));
    row_panel->SetSizer(row);
    row_panel->SetMinSize(wxSize(-1, FromDIP(34)));
    sizer->Add(row_panel, 0, wxEXPAND | wxBOTTOM, FromDIP(5));
    return value;
}

void PrintbenchNativePanel::on_camera_action(wxCommandEvent& event)
{
    if (!m_machine || !m_machine->is_connected() || !m_machine->has_ipcam)
        return;

    switch (event.GetId()) {
    case ID_PB_CAMERA_RECORD:
        m_machine->command_ipcam_record(!m_machine->camera_recording_when_printing);
        break;
    case ID_PB_CAMERA_TIMELAPSE:
        if (!m_machine->is_support_timelapse || m_machine->printer_type == "N7")
            return;
        m_machine->command_ipcam_timelapse(!m_machine->camera_timelapse);
        break;
    case ID_PB_CAMERA_RESOLUTION: {
        const auto& modes = m_machine->camera_resolution_supported;
        if (modes.size() <= 1)
            return;
        auto it = std::find(modes.begin(), modes.end(), m_machine->camera_resolution);
        const size_t index = it == modes.end() ? 0 : (static_cast<size_t>(std::distance(modes.begin(), it)) + 1) % modes.size();
        m_machine->command_ipcam_resolution_set(modes[index]);
        break;
    }
    default:
        break;
    }
}

void PrintbenchNativePanel::refresh_from_machine(MachineObject* machine)
{
    const bool machine_changed = machine != m_machine;
    m_machine = machine;
    if (m_media_play_ctrl) {
        m_media_play_ctrl->SetMachineObject(machine);
        if (machine_changed && machine != nullptr && machine->is_connected())
            m_media_play_ctrl->jump_to_play();
    }
    apply_snapshot(m_collector.collect(machine));
}

void PrintbenchNativePanel::apply_snapshot(const PrintbenchSnapshot& s)
{
    observe_history(s);
    if (m_header_status)
        m_header_status->SetSnapshot(s.online, wxString::FromUTF8(s.wifi_signal));
    if (m_hero_panel)
        m_hero_panel->SetSnapshot(s.online, wxString::FromUTF8(s.print_state));
    const bool ready = s.online && (s.print_state == "IDLE" || s.print_state == "FINISH");
    if (m_status_ready) {
        m_status_ready->SetLabel(ready ? L"Bereit" : (s.online ? wxString::FromUTF8(s.print_state) : L"Offline"));
        m_status_ready->SetForegroundColour(ready ? PB_OK : (s.online ? PB_TEXT : PB_MUTED));
    }
    const wxString wifi = s.wifi_signal.empty() ? "--" : wxString::FromUTF8(s.wifi_signal);
    const std::array<wxString, 6> device_values{
        s.online ? wxString(L"●  Verbunden") : wxString(L"●  Offline"),
        s.has_camera ? wxString(L"●  Ready") : wxString(L"●  --"),
        s.has_ams ? wxString(L"●  Verbunden") : wxString(L"●  --"),
        wxString(L"●  ") + wifi,
        wxString(L"●  Aktiv"),
        wxString(L"●  Nicht erforderlich")};
    const std::array<bool, 6> device_ok{
        s.online, s.has_camera, s.has_ams, s.online && !s.wifi_signal.empty(), true, true};
    if (m_sidebar_devices[0])
        m_sidebar_devices[0]->SetState(s.online, s.online ? "Online" : "Offline");
    if (m_sidebar_devices[1])
        m_sidebar_devices[1]->SetState(s.has_ams, s.has_ams ? "Verbunden" : "Nicht verbunden");
    for (size_t i = 0; i < m_device_status_cells.size(); ++i) {
        if (!m_device_status_cells[i]) continue;
        wxString value = device_values[i];
        value.Replace(L"●  ", wxEmptyString);
        m_device_status_cells[i]->SetState(value, device_ok[i]);
    }

    const bool active_print = s.print_state == "RUNNING" || s.print_state == "PAUSE";
    if (m_job_header)
        m_job_header->SetJob(wxString::FromUTF8(s.job_name), wxString::FromUTF8(s.print_state), active_print);
    const int progress_value = active_print ? std::clamp(s.progress, 0, 100) : 0;
    if (m_progress_gauge)
        m_progress_gauge->SetValue(progress_value);
    if (active_print) {
        m_progress->SetLabel(wxString::Format("%d %%", progress_value));
        m_progress->SetForegroundColour(PB_OK);
        m_layers->SetLabel(wxString::Format("%d / %d", s.layer_current, s.layer_total));
        const int minutes = std::max(0, s.remaining_seconds / 60);
        if (minutes >= 60)
            m_remaining->SetLabel(wxString::Format("%d h %02d min", minutes / 60, minutes % 60));
        else
            m_remaining->SetLabel(wxString::Format("%d min", minutes));
    } else {
        m_progress->SetLabel("--");
        m_progress->SetForegroundColour(PB_TEXT);
        m_layers->SetLabel("--");
        m_remaining->SetLabel("--");
    }

    m_nozzle->SetLabel(format_temp(s.nozzle_c, s.nozzle_target_c));
    m_bed->SetLabel(format_temp(s.bed_c, s.bed_target_c));
    m_chamber->SetLabel(format_temp(s.chamber_c));
    static const std::array<wxString, 5> speed_labels{L"--", L"Leise (50 %)", L"Standard (100 %)", L"Sport (124 %)", L"Ludicrous (166 % )"};
    const int speed_idx = std::clamp(s.speed_level, 0, 4);
    if (m_speed) m_speed->SetLabel(speed_labels[static_cast<size_t>(speed_idx)]);
    if (m_ams_summary) {
        int loaded = 0;
        for (const auto& slot : s.ams_slots) loaded += slot.present ? 1 : 0;
        m_ams_summary->SetLabel(s.has_ams ? wxString::Format("%d/4 Slots geladen", loaded) : "Nicht verbunden");
    }
    const std::array<wxColour, 6> printer_status_colours{
        ready ? PB_OK : (s.online ? PB_ACCENT : PB_MUTED),
        s.online ? PB_ACCENT : PB_MUTED,
        s.online ? PB_ACCENT : PB_MUTED,
        s.online ? PB_ACCENT : PB_MUTED,
        active_print ? PB_OK : (s.online ? PB_ACCENT : PB_MUTED),
        s.has_ams ? PB_OK : PB_MUTED};
    for (size_t i = 0; i < m_printer_status_dots.size(); ++i) {
        if (m_printer_status_dots[i])
            m_printer_status_dots[i]->SetForegroundColour(printer_status_colours[i]);
    }
    if (m_temp_values[0]) m_temp_values[0]->SetLabel(wxString::Format("%d C", s.nozzle_c));
    if (m_temp_values[1]) m_temp_values[1]->SetLabel(wxString::Format("%d C", s.bed_c));
    if (m_temp_values[2]) m_temp_values[2]->SetLabel(wxString::Format("%.0f C", s.chamber_c));
    if (m_temp_chart)
        m_temp_chart->push(s.nozzle_c, s.bed_c, s.chamber_c);

    wxString camera = s.has_camera ? "READY" : "NOT AVAILABLE";
    if (s.has_camera && !s.camera_resolution.empty())
        camera += "  " + wxString::FromUTF8(s.camera_resolution);
    if (s.camera_recording)
        camera += "  REC";
    if (s.camera_timelapse)
        camera += "  TL";
    m_camera->SetLabel(camera);
    const bool camera_connected = m_machine != nullptr && m_machine->is_connected() && s.has_camera;
    if (m_camera_record) {
        m_camera_record->Enable(camera_connected);
        m_camera_record->SetCaption(s.camera_recording ? "STOP AUFNAHME" : "AUFNAHME");
        m_camera_record->SetAlert(s.camera_recording);
    }
    if (m_camera_timelapse) {
        const bool timelapse_control = camera_connected && s.camera_timelapse_control_supported;
        m_camera_timelapse->Enable(timelapse_control);
        m_camera_timelapse->SetCaption(s.camera_timelapse ? "TIMELAPSE AUS" : "TIMELAPSE");
        m_camera_timelapse->SetAlert(s.camera_timelapse);
        m_camera_timelapse->SetToolTip(timelapse_control
            ? "Timelapse am Drucker umschalten"
            : (camera_connected ? "P2S-Firmware meldet Timelapse, lehnt direkte LAN-Steuerung jedoch ab"
                                : "Kamera nicht verbunden"));
    }
    if (m_camera_resolution) {
        const bool has_modes = camera_connected && m_machine && m_machine->camera_resolution_supported.size() > 1;
        m_camera_resolution->Enable(has_modes);
        const wxString resolution = s.camera_resolution.empty() ? wxString::FromUTF8("AUFLÖSUNG") : wxString::FromUTF8(s.camera_resolution);
        m_camera_resolution->SetCaption(resolution);
    }

    if (m_ams_environment)
        m_ams_environment->SetEnvironment(s.has_ams, s.ams_temp_c, s.ams_humidity);

    const bool connected = m_machine != nullptr && m_machine->is_connected();
    const bool pausable = connected && (s.print_state == "RUNNING" || s.print_state == "PAUSE");
    if (m_pause_resume) {
        m_pause_resume->Enable(pausable);
        m_pause_resume->SetCaption(s.print_state == "PAUSE" ? "FORTSETZEN" : "PAUSE");
    }
    if (m_stop)
        m_stop->Enable(connected && (s.print_state == "RUNNING" || s.print_state == "PAUSE"));
    for (size_t i = 0; i < m_speed_buttons.size(); ++i) {
        if (!m_speed_buttons[i]) continue;
        const bool active = static_cast<int>(i) + 1 == s.speed_level;
        m_speed_buttons[i]->Enable(connected && (s.print_state == "RUNNING" || s.print_state == "PAUSE"));
        m_speed_buttons[i]->SetActive(active);
    }
    if (m_light) {
        auto* lamp = connected && m_machine != nullptr ? m_machine->GetLamp() : nullptr;
        m_light->Enable(lamp != nullptr);
        m_light->SetCaption(lamp != nullptr && lamp->IsChamberLightOn() ? "LICHT AUS" : "LICHT AN");
    }

    for (size_t i = 0; i < m_ams_slots.size(); ++i) {
        const auto& slot = s.ams_slots[i];
        wxColour colour(40, 62, 75);
        if (slot.present && slot.color.size() >= 6) {
            unsigned long rgb = 0;
            if (wxString::FromUTF8(slot.color.substr(0, 6)).ToULong(&rgb, 16))
                colour = wxColour((rgb >> 16) & 0xff, (rgb >> 8) & 0xff, rgb & 0xff);
        }
        const wxString material = slot.material.empty() ? wxString() : wxString::FromUTF8(slot.material);
        if (m_ams_slots[i])
            m_ams_slots[i]->set_slot(slot.present, material, colour, slot.remain);
    }
    Layout();
}

void PrintbenchNativePanel::activate_top_nav(size_t index)
{
    if (index >= m_top_nav.size())
        return;
    for (size_t i = 0; i < m_top_nav.size(); ++i)
        if (m_top_nav[i])
            m_top_nav[i]->SetActive(i == index);
}

void PrintbenchNativePanel::activate_nav(size_t index)
{
    if (index >= m_nav_rows.size())
        return;
    for (size_t i = 0; i < m_nav_rows.size(); ++i)
        if (m_nav_rows[i])
            m_nav_rows[i]->SetActive(i == index);
}

void PrintbenchNativePanel::scroll_to(wxWindow* target)
{
    if (!target)
        return;
    const int step = std::max(1, FromDIP(12));
    // Cards live in nested sizers. Their local y-coordinate is not the
    // dashboard's scroll coordinate, so convert through screen coordinates.
    int view_x = 0, view_y = 0;
    GetViewStart(&view_x, &view_y);
    const int target_content_y = view_y * step +
        (target->GetScreenPosition().y - GetScreenPosition().y);
    Scroll(-1, std::max(0, target_content_y / step));
    target->SetFocus();
}

void PrintbenchNativePanel::navigate_to_section(size_t index)
{
    handle_nav(index);
}

void PrintbenchNativePanel::handle_nav(size_t index)
{
    activate_nav(index);
    switch (index) {
    case 0: activate_top_nav(0); break;
    case 3: case 4: activate_top_nav(3); break;
    case 6: activate_top_nav(4); break;
    case 7: activate_top_nav(1); break;
    case 9: case 10: activate_top_nav(2); break;
    case 11: case 13: activate_top_nav(5); break;
    default: break;
    }
    switch (index) {
    case 0: Scroll(0, 0); break;                              // Uebersicht
    case 1: scroll_to(m_camera_card); break;                  // Live Ansicht
    case 2: scroll_to(m_quick_card); break;                   // Steuerung
    case 3: scroll_to(m_ams_card); break;                     // AMS 2 Pro
    case 4: scroll_to(m_ams_card); break;                     // Material
    case 5: scroll_to(m_print_card); break;                   // Druckauftraege
    case 6: scroll_to(m_history_card); break;                 // Historie
    case 7: if (wxGetApp().mainframe) wxGetApp().mainframe->select_tab(MainFrame::tp3DEditor); break;
    case 8: scroll_to(m_camera_card); break;                  // Kamera
    case 9: if (wxGetApp().mainframe) wxGetApp().mainframe->select_tab(MainFrame::tpMultiDevice); break;
    case 10: if (wxGetApp().mainframe) wxGetApp().mainframe->select_tab(MainFrame::tpMultiDevice); break;
    case 11: wxGetApp().open_preferences(); break;            // Sicherheit / Einstellungen
    case 12: if (wxGetApp().mainframe) wxGetApp().mainframe->show_log_window(); break;
    case 13: scroll_to(m_action_card); break;                     // System
    default: break;
    }
}

void PrintbenchNativePanel::observe_history(const PrintbenchSnapshot& s)
{
    const bool active = s.print_state == "RUNNING" || s.print_state == "PAUSE";
    const bool was_active = m_previous_print_state == "RUNNING" || m_previous_print_state == "PAUSE";

    if (active && !m_history_tracking) {
        m_history_tracking = true;
        m_history_started = std::chrono::steady_clock::now();
        m_history_job_name = s.job_name.empty() ? "Druckauftrag" : wxString::FromUTF8(s.job_name);
    } else if (active && !s.job_name.empty()) {
        m_history_job_name = wxString::FromUTF8(s.job_name);
    }

    if (m_history_tracking && was_active && !active && s.online) {
        const int observed_seconds = static_cast<int>(std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now() - m_history_started).count());
        wxString status = "Beendet";
        if (s.print_state == "FINISH")
            status = "Fertig";
        else if (s.print_state == "FAILED" || s.print_state == "ERROR")
            status = "Fehler";
        else if (s.print_state == "CANCEL" || s.print_state == "CANCELLED")
            status = "Abgebrochen";
        append_history(m_history_job_name, status, observed_seconds);
        m_history_tracking = false;
        m_history_job_name.clear();
    }

    // Going offline is not proof that a print ended. Keep tracking and wait for
    // a later online state instead of manufacturing a false history entry.
    if (s.online)
        m_previous_print_state = s.print_state;
}

void PrintbenchNativePanel::append_history(const wxString& job_name, const wxString& status, int observed_seconds)
{
    HistoryEntry entry;
    entry.finished_at = wxDateTime::Now().Format("%d.%m. %H:%M");
    entry.status = status;
    entry.job_name = job_name.empty() ? "Druckauftrag" : job_name;
    entry.observed_seconds = std::max(0, observed_seconds);
    m_history.push_front(entry);
    while (m_history.size() > 20)
        m_history.pop_back();
    save_history();
    update_history_ui();
}

void PrintbenchNativePanel::update_history_ui()
{
    for (auto* row : m_history_rows)
        if (row) row->clear();

    if (m_history.empty()) {
        if (m_history_rows[0])
            m_history_rows[0]->set_empty_state(wxString::FromUTF8("Noch keine lokalen Druckabschlüsse."));
        return;
    }

    for (size_t i = 0; i < std::min(m_history_rows.size(), m_history.size()); ++i) {
        const auto& entry = m_history[i];
        const int minutes = entry.observed_seconds / 60;
        const wxString duration = minutes >= 60
            ? wxString::Format("%dh %02dm", minutes / 60, minutes % 60)
            : wxString::Format("%dm", minutes);
        m_history_rows[i]->set_entry(entry.job_name, entry.finished_at, duration, entry.status);
    }
}

void PrintbenchNativePanel::load_history()
{
    const wxString dir = wxStandardPaths::Get().GetUserLocalDataDir();
    const wxString path = wxFileName(dir, "printbench-print-history.tsv").GetFullPath();
    if (!wxFileExists(path))
        return;

    wxTextFile file;
    if (!file.Open(path))
        return;
    for (size_t i = 0; i < file.GetLineCount() && m_history.size() < 20; ++i) {
        const wxArrayString fields = wxSplit(file.GetLine(i), '\t', '\0');
        if (fields.size() != 4)
            continue;
        long seconds = 0;
        fields[2].ToLong(&seconds);
        HistoryEntry entry{fields[0], fields[1], fields[3], static_cast<int>(std::max(0L, seconds))};
        m_history.push_back(entry);
    }
    file.Close();
}

void PrintbenchNativePanel::save_history() const
{
    const wxString dir = wxStandardPaths::Get().GetUserLocalDataDir();
    if (!wxDirExists(dir))
        wxFileName::Mkdir(dir, wxS_DIR_DEFAULT, wxPATH_MKDIR_FULL);
    const wxString path = wxFileName(dir, "printbench-print-history.tsv").GetFullPath();
    wxTextFile file;
    if (wxFileExists(path)) {
        if (!file.Open(path))
            return;
        file.Clear();
    } else if (!file.Create(path)) {
        return;
    }

    for (const auto& entry : m_history) {
        wxString safe_name = entry.job_name;
        safe_name.Replace("\t", " ");
        safe_name.Replace("\r", " ");
        safe_name.Replace("\n", " ");
        file.AddLine(wxString::Format("%s\t%s\t%d\t%s", entry.finished_at, entry.status, entry.observed_seconds, safe_name));
    }
    file.Write();
    file.Close();
}

} // namespace GUI
} // namespace Slic3r
