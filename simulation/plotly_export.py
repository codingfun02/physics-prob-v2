"""Plotly HTML 저장 — 모바일·iframe 뷰어 대응."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import plotly.graph_objects as go

from config import (
    CHART_BAR_LABEL_SIZE_MOBILE,
    CHART_PROB_REF_LINE_WIDTH_MOBILE,
    CHART_TITLE_LINE_GAP_MOBILE,
    CHART_TITLE_MAIN_SIZE_MOBILE,
    CHART_TITLE_SUB_SIZE_MOBILE,
    DENSITY_AXIS_LIM_MOBILE,
    DENSITY_CAMERA_EYE_MOBILE,
    DENSITY_HTML_COLORBAR_LEN_MOBILE,
    DENSITY_HTML_COLORBAR_THICKNESS_MOBILE,
    DENSITY_HTML_COLORBAR_XANCHOR_MOBILE,
    DENSITY_HTML_COLORBAR_X_MOBILE,
    DENSITY_HTML_MARGIN_R_MOBILE,
    DENSITY_HTML_SCENE_X_MOBILE,
    DENSITY_HTML_SCENE_Y_MOBILE,
    OUTPUT_DIR,
)
from simulation.output_layout import png_export_path

_MODEBAR_HIDE_CSS = """
  @media (max-width: 768px) {
    .modebar-container { display: none !important; }
  }
"""

_MOBILE_HEAD = """<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
  html, body {
    margin: 0; padding: 0; width: 100%; min-height: 100%;
    overflow-x: hidden; -webkit-text-size-adjust: 100%;
  }
  .plotly-graph-div, .js-plotly-plot {
    width: 100% !important;
    min-height: min(88dvh, 720px);
  }
  @media (max-width: 768px) {
    html, body { height: 100%; min-height: 0; }
    .plotly-graph-div, .js-plotly-plot {
      height: 100% !important;
      min-height: min(62dvh, 520px) !important;
    }
  }
""" + _MODEBAR_HIDE_CSS + """
</style>
"""

_DENSITY_HEAD = """<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
  html, body {
    margin: 0; padding: 0; width: 100%; height: 100%;
    overflow: hidden; -webkit-text-size-adjust: 100%;
    background: #fafbfc;
  }
  body > div {
    height: 100% !important;
    width: 100% !important;
  }
  .plotly-graph-div, .js-plotly-plot {
    width: 100% !important;
    height: 100% !important;
    min-height: 100% !important;
  }
  @media (max-width: 768px) {
    html, body { min-height: 100dvh; }
    .plotly-graph-div, .js-plotly-plot {
      min-height: 0 !important;
      touch-action: pan-x pan-y pinch-zoom;
    }
  }
""" + _MODEBAR_HIDE_CSS + """
</style>
"""

_PROBABILITY_HEAD = """<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
  html, body {
    margin: 0; padding: 0; width: 100%; min-height: 100%;
    overflow-x: hidden; -webkit-text-size-adjust: 100%;
    background: #fff;
  }
  .plotly-graph-div, .js-plotly-plot {
    width: 100% !important;
    min-height: min(90dvh, 820px);
  }
  @media (max-width: 768px) {
    html, body { height: 100%; min-height: 0; overflow-x: hidden; }
    .plotly-graph-div, .js-plotly-plot {
      height: 100% !important;
      min-height: 0 !important;
    }
  }
""" + _MODEBAR_HIDE_CSS + """
</style>
"""

_COMPARISON_HEAD = """<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
  html, body {
    margin: 0; padding: 0; width: 100%; min-height: 100%;
    overflow-x: hidden; -webkit-text-size-adjust: 100%;
    background: #fff;
  }
  .plotly-graph-div, .js-plotly-plot {
    width: 100% !important;
    min-height: min(90dvh, 820px);
  }
  @media (max-width: 768px) {
    html, body {
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }
    body > div {
      height: 100% !important;
      min-height: 0 !important;
      width: 100% !important;
    }
    .plotly-graph-div, .js-plotly-plot {
      width: 100% !important;
      height: 100% !important;
      min-height: 0 !important;
    }
  }
""" + _MODEBAR_HIDE_CSS + """
</style>
"""

_RESIZE_SCRIPT = """<script>
  var _CHART_KIND = "__CHART_KIND__";
  var _TITLE_GAP_MOBILE = __TITLE_GAP_MOBILE__;
  var _TITLE_MAIN_MOBILE = __TITLE_MAIN_MOBILE__;
  var _TITLE_SUB_MOBILE = __TITLE_SUB_MOBILE__;
  var _BAR_LABEL_MOBILE = __BAR_LABEL_MOBILE__;
  var _PROB_REF_LINE_WIDTH_MOBILE = __PROB_REF_LINE_WIDTH_MOBILE__;
  var _DENSITY_MARGIN_R_MOBILE = __DENSITY_MARGIN_R_MOBILE__;
  var _DENSITY_COLORBAR_X_MOBILE = __DENSITY_COLORBAR_X_MOBILE__;
  var _DENSITY_COLORBAR_XANCHOR_MOBILE = "__DENSITY_COLORBAR_XANCHOR_MOBILE__";
  var _DENSITY_COLORBAR_THICKNESS_MOBILE = __DENSITY_COLORBAR_THICKNESS_MOBILE__;
  var _DENSITY_COLORBAR_LEN_MOBILE = __DENSITY_COLORBAR_LEN_MOBILE__;
  var _DENSITY_SCENE_X_MOBILE = __DENSITY_SCENE_X_MOBILE__;
  var _DENSITY_SCENE_Y_MOBILE = __DENSITY_SCENE_Y_MOBILE__;
  var _DENSITY_AXIS_LIM_MOBILE = __DENSITY_AXIS_LIM_MOBILE__;
  var _DENSITY_CAMERA_EYE_MOBILE = __DENSITY_CAMERA_EYE_MOBILE__;
  var _layoutDesktop = null;
  var _resizeTimer = null;
  var _resizeSeq = 0;
  var _afterPlotBound = false;
  var _applyingLayout = false;

  function _stripHtml(text) {
    return (text || "").replace(/<[^>]+>/g, "");
  }

  function _fitTitleSizes(plot) {
    var w = (plot && plot.clientWidth) || document.documentElement.clientWidth || 390;
    var widthScale = Math.min(1, Math.max(0.55, w / 520));
    var ly = plot && plot.layout && plot.layout.title;
    var mainText = ly ? _stripHtml(ly.text) : "";
    var subText = ly && ly.subtitle ? (ly.subtitle.text || "") : "";
    var mainLen = mainText.length || 1;
    var subLen = subText.length || 1;
    var pxPerChar = 0.58;
    var mainFromText = Math.floor(w / (mainLen * pxPerChar));
    var subFromText = Math.floor(w / (subLen * pxPerChar));
    var mainScaled = Math.round(_TITLE_MAIN_MOBILE * widthScale);
    var subScaled = Math.round(_TITLE_SUB_MOBILE * widthScale);
    return {
      main: Math.max(12, Math.min(mainScaled, mainFromText)),
      sub: Math.max(10, Math.min(subScaled, subFromText)),
    };
  }

  function _uniformRefLineTrace(plot) {
    for (var i = 0; i < (plot.data || []).length; i++) {
      var tr = plot.data[i];
      if (tr.type === "scatter" && tr.mode === "lines" && tr.name && tr.name.indexOf("균일") === 0) {
        return i;
      }
    }
    return null;
  }

  function _uniformRefLineWidthMobile(plot) {
    var w = (plot && plot.clientWidth) || document.documentElement.clientWidth || 390;
    var scale = Math.min(1, Math.max(0.5, w / 520));
    return Math.round(Math.max(0.6, _PROB_REF_LINE_WIDTH_MOBILE * scale) * 10) / 10;
  }

  function _restyleUniformRefLine(plot, width) {
    var idx = _uniformRefLineTrace(plot);
    if (idx == null) return Promise.resolve();
    return window.Plotly.restyle(plot, { "line.width": [width] }, [idx]);
  }

  function _applyUniformRefLineMobile(plot) {
    if (_CHART_KIND !== "probability" && _CHART_KIND !== "comparison") return Promise.resolve();
    return _restyleUniformRefLine(plot, _uniformRefLineWidthMobile(plot));
  }

  function _comparisonBarCount(plot) {
    var n = 0;
    for (var i = 0; i < (plot.data || []).length; i++) {
      if (plot.data[i].type === "bar") n++;
    }
    return n;
  }

  function _comparisonLegendRows(plot) {
    return Math.max(1, Math.ceil(_comparisonBarCount(plot) / 2));
  }

  function _comparisonTopMargin(plot) {
    var sizes = _fitTitleSizes(plot);
    var gap = _TITLE_GAP_MOBILE != null ? _TITLE_GAP_MOBILE : 0;
    return Math.round(sizes.main + sizes.sub + gap + 10);
  }

  function _comparisonBottomMargin(plot) {
    return Math.round(12 + _comparisonLegendRows(plot) * 11);
  }

  function _comparisonLegendY(plot) {
    var rows = _comparisonLegendRows(plot);
    return -(0.035 + (rows - 1) * 0.016);
  }

  function _prepareComparisonMobile(plot) {
    if (_CHART_KIND !== "comparison" || !_isMobile() || !plot) return;
    var h = document.documentElement.clientHeight || window.innerHeight || 640;
    document.documentElement.style.height = h + "px";
    document.body.style.height = h + "px";
    plot.style.height = "100%";
    plot.style.minHeight = "0";
    var el = plot.parentElement;
    while (el && el !== document.body) {
      el.style.height = "100%";
      el.style.minHeight = "0";
      el = el.parentElement;
    }
  }

  function _comparisonMobileRelayout(plot) {
    var sizes = _fitTitleSizes(plot);
    var upd = _applyTitleGapMobile({});
    upd["title.font.size"] = sizes.main;
    upd["title.subtitle.font.size"] = sizes.sub;
    upd["title.pad.t"] = 2;
    Object.assign(upd, {
      margin: {
        t: _comparisonTopMargin(plot),
        r: 8,
        l: 36,
        b: _comparisonBottomMargin(plot),
      },
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: _comparisonLegendY(plot),
        yanchor: "top",
        font: { size: 7 },
        tracegroupgap: 1,
      },
    });
    return window.Plotly.relayout(plot, upd).then(function() {
      _prepareComparisonMobile(plot);
      return _applyUniformRefLineMobile(plot);
    });
  }

  function _isMobile() {
    if (window.matchMedia("(max-width: 768px)").matches) return true;
    var docW = document.documentElement.clientWidth || 0;
    var innerW = window.innerWidth || 0;
    var w = docW > 0 ? Math.min(docW, innerW || docW) : innerW;
    return w > 0 && w <= 768;
  }

  function _marginOf(m) {
    if (!m) return {};
    return { t: m.t, r: m.r, b: m.b, l: m.l };
  }

  function _textLabelTraces(plot) {
    var idx = [];
    for (var i = 0; i < plot.data.length; i++) {
      if (plot.data[i].type === "scatter" && plot.data[i].mode === "text") {
        idx.push(i);
      }
    }
    return idx;
  }

  function _captureDesktop(plot) {
    if (_layoutDesktop) return;
    var ly = plot.layout;
    _layoutDesktop = {
      margin: _marginOf(ly.margin),
      titlePadB: ly.title && ly.title.pad ? ly.title.pad.b : null,
      titleFontSize: ly.title && ly.title.font ? ly.title.font.size : null,
      titleSubtitleFontSize:
        ly.title && ly.title.subtitle && ly.title.subtitle.font
          ? ly.title.subtitle.font.size
          : null,
      textLabelTraces: _textLabelTraces(plot),
      textLabelSizes: [],
      legend: ly.legend ? {
        orientation: ly.legend.orientation,
        x: ly.legend.x,
        y: ly.legend.y,
        xanchor: ly.legend.xanchor,
        yanchor: ly.legend.yanchor,
        font: ly.legend.font ? { size: ly.legend.font.size } : undefined,
      } : null,
      uniformRefLineTrace: null,
      uniformRefLineWidth: null,
      sceneDomain: null,
      sceneAxisX: null,
      sceneAxisY: null,
      sceneAxisZ: null,
      sceneCameraEye: null,
      colorbarTrace: null,
      colorbarX: null,
      colorbarXanchor: null,
      colorbarThickness: null,
      colorbarLen: null,
    };
    _layoutDesktop.textLabelTraces.forEach(function(i) {
      var tf = plot.data[i].textfont;
      _layoutDesktop.textLabelSizes.push(tf && tf.size != null ? tf.size : null);
    });
    if (_CHART_KIND === "probability" || _CHART_KIND === "comparison") {
      _layoutDesktop.uniformRefLineTrace = _uniformRefLineTrace(plot);
      if (_layoutDesktop.uniformRefLineTrace != null) {
        var ln = plot.data[_layoutDesktop.uniformRefLineTrace].line;
        _layoutDesktop.uniformRefLineWidth = ln && ln.width != null ? ln.width : 1.5;
      }
    }
    if (_CHART_KIND === "density" && ly.scene && ly.scene.domain) {
      _layoutDesktop.sceneDomain = {
        x: (ly.scene.domain.x || []).slice(),
        y: (ly.scene.domain.y || []).slice(),
      };
      if (ly.scene.xaxis && ly.scene.xaxis.range) {
        _layoutDesktop.sceneAxisX = ly.scene.xaxis.range.slice();
      }
      if (ly.scene.yaxis && ly.scene.yaxis.range) {
        _layoutDesktop.sceneAxisY = ly.scene.yaxis.range.slice();
      }
      if (ly.scene.zaxis && ly.scene.zaxis.range) {
        _layoutDesktop.sceneAxisZ = ly.scene.zaxis.range.slice();
      }
      if (ly.scene.camera && ly.scene.camera.eye) {
        _layoutDesktop.sceneCameraEye = Object.assign({}, ly.scene.camera.eye);
      }
      for (var i = 0; i < plot.data.length; i++) {
        if (plot.data[i].showscale) {
          _layoutDesktop.colorbarTrace = i;
          var cb = plot.data[i].colorbar || {};
          _layoutDesktop.colorbarX = cb.x;
          _layoutDesktop.colorbarXanchor = cb.xanchor;
          _layoutDesktop.colorbarThickness = cb.thickness;
          _layoutDesktop.colorbarLen = cb.len;
          break;
        }
      }
    }
  }

  function _applyTitleGapMobile(upd) {
    if (_TITLE_GAP_MOBILE != null) {
      upd["title.pad.b"] = _TITLE_GAP_MOBILE;
    }
    return upd;
  }

  function _applyTitleSizeMobile(upd, plot) {
    if (_CHART_KIND === "density" || _CHART_KIND === "probability" || _CHART_KIND === "comparison") {
      var sizes = _fitTitleSizes(plot);
      upd["title.font.size"] = sizes.main;
      upd["title.subtitle.font.size"] = sizes.sub;
    }
    return upd;
  }

  function _densityMobileRelayout(plot) {
    var lim = _DENSITY_AXIS_LIM_MOBILE;
    var t = _layoutDesktop.margin.t;
    var upd = _applyTitleSizeMobile(_applyTitleGapMobile({}), plot);
    Object.assign(upd, {
      margin: { t: t, r: _DENSITY_MARGIN_R_MOBILE, l: 0, b: 0 },
      "scene.domain.x": _DENSITY_SCENE_X_MOBILE.slice(),
      "scene.domain.y": _DENSITY_SCENE_Y_MOBILE.slice(),
      "scene.xaxis.range": [-lim, lim],
      "scene.yaxis.range": [-lim, lim],
      "scene.zaxis.range": [-lim, lim],
      "scene.camera.eye": _DENSITY_CAMERA_EYE_MOBILE,
      legend: { x: 0.02, y: 0.04, font: { size: 9 } },
    });
    return window.Plotly.relayout(plot, upd).then(function() {
      if (_layoutDesktop.colorbarTrace == null) return;
      return window.Plotly.restyle(
        plot,
        {
          "colorbar.x": [_DENSITY_COLORBAR_X_MOBILE],
          "colorbar.xanchor": [_DENSITY_COLORBAR_XANCHOR_MOBILE],
          "colorbar.thickness": [_DENSITY_COLORBAR_THICKNESS_MOBILE],
          "colorbar.len": [_DENSITY_COLORBAR_LEN_MOBILE],
        },
        [_layoutDesktop.colorbarTrace]
      );
    });
  }

  function _densityLayoutDrifted(plot) {
    if (_CHART_KIND !== "density" || !_layoutDesktop) return false;
    if (_densityMarginDrifted(plot)) return true;
    var ly = plot.layout || {};
    var sx = ly.scene && ly.scene.domain ? ly.scene.domain.x : null;
    if (!sx || sx[0] !== _DENSITY_SCENE_X_MOBILE[0] || sx[1] !== _DENSITY_SCENE_X_MOBILE[1]) {
      return true;
    }
    for (var i = 0; i < (plot.data || []).length; i++) {
      if (!plot.data[i].showscale) continue;
      var cb = plot.data[i].colorbar || {};
      if (cb.x !== _DENSITY_COLORBAR_X_MOBILE) return true;
      if (cb.xanchor !== _DENSITY_COLORBAR_XANCHOR_MOBILE) return true;
      return false;
    }
    return true;
  }

  function _earlyMobileLayout() {
    var plot = document.querySelector(".js-plotly-plot");
    if (!plot || !window.Plotly || !_isMobile()) return Promise.resolve();
    _captureDesktop(plot);
    _bindAfterPlot(plot);
    if (_CHART_KIND === "density") {
      return _densityMobileRelayout(plot);
    }
    return _applyMobile(plot);
  }
  window._earlyMobileLayout = _earlyMobileLayout;

  function _densityMarginDrifted(plot) {
    if (_CHART_KIND !== "density" || !_layoutDesktop) return false;
    var m = plot.layout && plot.layout.margin;
    if (!m) return true;
    return m.r !== _DENSITY_MARGIN_R_MOBILE
      || m.l !== 0
      || m.b !== 0;
  }

  function _bindAfterPlot(plot) {
    if (_afterPlotBound) return;
    _afterPlotBound = true;
    plot.on("plotly_afterplot", function() {
      if (_applyingLayout || !_isMobile() || _CHART_KIND !== "density") return;
      if (_densityLayoutDrifted(plot)) {
        _applyingLayout = true;
        _densityMobileRelayout(plot).finally(function() {
          _applyingLayout = false;
        });
      }
    });
  }

  function _applyMobile(plot) {
    var t = _layoutDesktop.margin.t;
    var upd = _applyTitleSizeMobile(_applyTitleGapMobile({}), plot);
    if (_CHART_KIND === "probability") {
      Object.assign(upd, {
        margin: { t: t, r: 12, l: 40, b: 88 },
        legend: {
          orientation: "h",
          x: 0.5,
          xanchor: "center",
          y: -0.2,
          yanchor: "top",
          font: { size: 10 },
        },
      });
      return window.Plotly.relayout(plot, upd).then(function() {
        if (_layoutDesktop.textLabelTraces.length) {
          var sizes = _layoutDesktop.textLabelTraces.map(function() {
            return _BAR_LABEL_MOBILE;
          });
          return window.Plotly.restyle(
            plot,
            { "textfont.size": sizes },
            _layoutDesktop.textLabelTraces
          );
        }
      }).then(function() {
        return _applyUniformRefLineMobile(plot);
      });
    }
    if (_CHART_KIND === "comparison") {
      return _comparisonMobileRelayout(plot);
    }
    if (_CHART_KIND === "density") {
      return _densityMobileRelayout(plot);
    }
    Object.assign(upd, { margin: { t: t, r: 8, l: 36, b: 48 } });
    return window.Plotly.relayout(plot, upd);
  }

  function _applyDesktop(plot) {
    if (!_layoutDesktop) return Promise.resolve();
    var upd = { margin: _layoutDesktop.margin };
    if (_layoutDesktop.titlePadB != null) {
      upd["title.pad.b"] = _layoutDesktop.titlePadB;
    }
    if (_layoutDesktop.titleFontSize != null) {
      upd["title.font.size"] = _layoutDesktop.titleFontSize;
    }
    if (_layoutDesktop.titleSubtitleFontSize != null) {
      upd["title.subtitle.font.size"] = _layoutDesktop.titleSubtitleFontSize;
    }
    if (_layoutDesktop.legend) upd.legend = _layoutDesktop.legend;
    if (_CHART_KIND === "density" && _layoutDesktop.sceneDomain) {
      upd["scene.domain.x"] = _layoutDesktop.sceneDomain.x;
      upd["scene.domain.y"] = _layoutDesktop.sceneDomain.y;
      if (_layoutDesktop.sceneAxisX) upd["scene.xaxis.range"] = _layoutDesktop.sceneAxisX;
      if (_layoutDesktop.sceneAxisY) upd["scene.yaxis.range"] = _layoutDesktop.sceneAxisY;
      if (_layoutDesktop.sceneAxisZ) upd["scene.zaxis.range"] = _layoutDesktop.sceneAxisZ;
      if (_layoutDesktop.sceneCameraEye) upd["scene.camera.eye"] = _layoutDesktop.sceneCameraEye;
    }
    return window.Plotly.relayout(plot, upd).then(function() {
      if (_layoutDesktop.textLabelTraces.length) {
        return window.Plotly.restyle(
          plot,
          { "textfont.size": _layoutDesktop.textLabelSizes },
          _layoutDesktop.textLabelTraces
        );
      }
    }).then(function() {
      if (_CHART_KIND === "density" && _layoutDesktop.colorbarTrace != null) {
        return window.Plotly.restyle(
          plot,
          {
            "colorbar.x": [_layoutDesktop.colorbarX],
            "colorbar.xanchor": [_layoutDesktop.colorbarXanchor],
            "colorbar.thickness": [_layoutDesktop.colorbarThickness],
            "colorbar.len": [_layoutDesktop.colorbarLen],
          },
          [_layoutDesktop.colorbarTrace]
        );
      }
    }).then(function() {
      if (
        (_CHART_KIND === "probability" || _CHART_KIND === "comparison")
        && _layoutDesktop.uniformRefLineTrace != null
        && _layoutDesktop.uniformRefLineWidth != null
      ) {
        return _restyleUniformRefLine(plot, _layoutDesktop.uniformRefLineWidth);
      }
    });
  }

  function _resizePlotly() {
    var plot = document.querySelector(".js-plotly-plot");
    if (!plot || !window.Plotly) return;
    var seq = ++_resizeSeq;
    _captureDesktop(plot);
    _bindAfterPlot(plot);
    var mobile = _isMobile();
    _applyingLayout = true;
    var apply = mobile ? _applyMobile(plot) : _applyDesktop(plot);
    Promise.resolve(apply).then(function() {
      if (seq !== _resizeSeq) return;
      if (mobile && _CHART_KIND === "comparison") {
        return window.Plotly.Plots.resize(plot).then(function() {
          _prepareComparisonMobile(plot);
        });
      }
      return window.Plotly.Plots.resize(plot);
    }).then(function() {
      if (seq !== _resizeSeq || !mobile || _CHART_KIND === "comparison") return;
      return _applyMobile(plot);
    }).finally(function() {
      if (seq === _resizeSeq) _applyingLayout = false;
    });
  }

  function _scheduleResize() {
    clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(_resizePlotly, 60);
  }

  window.addEventListener("load", function() {
    _earlyMobileLayout().finally(function() { _resizePlotly(); });
  });
  window.addEventListener("resize", _scheduleResize);
  window.addEventListener("orientationchange", function() { setTimeout(_resizePlotly, 300); });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", _scheduleResize);
  }
</script>
"""

_PLOTLY_CONFIG = {
    "responsive": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["sendDataToCloud"],
}

_HEAD_BY_KIND = {
    "density": _DENSITY_HEAD,
    "probability": _PROBABILITY_HEAD,
    "comparison": _COMPARISON_HEAD,
}

_EXPORT_PNG_KW = dict(width=1400, height=1000, scale=2)


def _resize_script(chart_kind: str) -> str:
    script = _RESIZE_SCRIPT.replace("__CHART_KIND__", chart_kind)
    script = script.replace("__TITLE_GAP_MOBILE__", str(CHART_TITLE_LINE_GAP_MOBILE))
    script = script.replace("__TITLE_MAIN_MOBILE__", str(CHART_TITLE_MAIN_SIZE_MOBILE))
    script = script.replace("__TITLE_SUB_MOBILE__", str(CHART_TITLE_SUB_SIZE_MOBILE))
    script = script.replace("__BAR_LABEL_MOBILE__", str(CHART_BAR_LABEL_SIZE_MOBILE))
    script = script.replace("__PROB_REF_LINE_WIDTH_MOBILE__", str(CHART_PROB_REF_LINE_WIDTH_MOBILE))
    script = script.replace("__DENSITY_MARGIN_R_MOBILE__", str(DENSITY_HTML_MARGIN_R_MOBILE))
    script = script.replace("__DENSITY_COLORBAR_X_MOBILE__", str(DENSITY_HTML_COLORBAR_X_MOBILE))
    script = script.replace("__DENSITY_COLORBAR_XANCHOR_MOBILE__", DENSITY_HTML_COLORBAR_XANCHOR_MOBILE)
    script = script.replace("__DENSITY_COLORBAR_THICKNESS_MOBILE__", str(DENSITY_HTML_COLORBAR_THICKNESS_MOBILE))
    script = script.replace("__DENSITY_COLORBAR_LEN_MOBILE__", str(DENSITY_HTML_COLORBAR_LEN_MOBILE))
    script = script.replace(
        "__DENSITY_SCENE_X_MOBILE__",
        "[" + ", ".join(str(v) for v in DENSITY_HTML_SCENE_X_MOBILE) + "]",
    )
    script = script.replace(
        "__DENSITY_SCENE_Y_MOBILE__",
        "[" + ", ".join(str(v) for v in DENSITY_HTML_SCENE_Y_MOBILE) + "]",
    )
    script = script.replace("__DENSITY_AXIS_LIM_MOBILE__", str(DENSITY_AXIS_LIM_MOBILE))
    script = script.replace(
        "__DENSITY_CAMERA_EYE_MOBILE__",
        json.dumps(DENSITY_CAMERA_EYE_MOBILE, separators=(",", ":")),
    )
    return script


def try_write_png_export(
    fig: go.Figure,
    html_path: str | Path,
    *,
    prep: Callable[[go.Figure], None] | None = None,
    png_kw: dict | None = None,
    output_dir: str | Path = OUTPUT_DIR,
) -> Path | None:
    """이미지 export용 PNG — output/png/ 에 저장."""
    png_path = png_export_path(html_path, output_dir)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        export_fig = go.Figure(fig) if prep else fig
        if prep:
            prep(export_fig)
        export_fig.write_image(str(png_path), **(png_kw or _EXPORT_PNG_KW))
        return png_path
    except Exception:
        return None


def write_plotly_html(
    fig: go.Figure,
    save_path: str | Path,
    *,
    chart_kind: str = "default",
) -> None:
    """반응형 Plotly HTML 저장 (대시보드 iframe·모바일 Safari)."""
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    fig.update_layout(autosize=True)
    fig.write_html(
        str(save_path),
        config=_PLOTLY_CONFIG,
        include_plotlyjs="cdn",
    )

    head = _HEAD_BY_KIND.get(chart_kind, _MOBILE_HEAD)
    bundle = head + _resize_script(chart_kind)
    text = save_path.read_text(encoding="utf-8")

    custom_head = re.compile(
        r"<meta name=\"viewport\" content=\"width=device-width.*?</script>\s*",
        re.DOTALL,
    )
    if custom_head.search(text):
        text = custom_head.sub(bundle, text, count=1)
    else:
        text = text.replace("<head>", "<head>\n" + bundle, 1)

    body_script = re.compile(
        r"<script>\s*var _CHART_KIND.*?</script>\s*(?=</body>)",
        re.DOTALL,
    )
    text = body_script.sub("", text)

    early_hook = '<script>if(window._earlyMobileLayout){window._earlyMobileLayout();}</script>'
    if early_hook not in text:
        marker = "};            </script>        </div>"
        if marker in text:
            text = text.replace(marker, "};            </script>" + early_hook + "        </div>", 1)

    save_path.write_text(text, encoding="utf-8")
