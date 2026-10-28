import Toybox.Graphics;
import Toybox.Math;

// Allocate native font heights before drawing. The primary/next touch rectangles
// remain unchanged; the title owns a two-line band above the workout fields.
module WorkoutLayout {
    function metrics(dc, w, h) {
        var gap = (h*0.008).toNumber();
        if (gap < 2) { gap = 2; }
        var tiny = dc.getFontHeight(Graphics.FONT_XTINY);
        var headerY = (h*0.065).toNumber();
        var headerBottom = headerY+tiny+gap;
        var titleTop = headerBottom+gap;
        var titleBottom = titleTop+2*tiny+gap;
        var fieldTop = titleBottom+2*gap;
        var fieldBottom = WorkoutControls.rect("primary",w,h)[1]-gap;
        var valueFont = Graphics.FONT_SMALL;
        if (fieldBottom-fieldTop < 2*tiny+dc.getFontHeight(valueFont)) { valueFont = Graphics.FONT_XTINY; }
        var valueHeight = dc.getFontHeight(valueFont);
        var spacing = (fieldBottom-fieldTop-2*tiny-valueHeight)/2;
        return {"gap"=>gap,"headerY"=>headerY,"headerBottom"=>headerBottom,
            "titleTop"=>titleTop,"titleBottom"=>titleBottom,"fieldTop"=>fieldTop,
            "labelY"=>fieldTop,"valueY"=>fieldTop+tiny+spacing,
            "detailY"=>fieldBottom-tiny,"fieldBottom"=>fieldBottom,"valueFont"=>valueFont};
    }
    // Width of the narrowest chord crossed by this text row, with an inset.
    function roundWidth(w, h, y, height) {
        var top = Math.abs(2.0*y/h-1);
        var bottom = Math.abs(2.0*(y+height)/h-1);
        var edge = top > bottom ? top : bottom;
        if (edge >= 1) { return 0; }
        return (w*Math.sqrt(1-edge*edge)-w*0.04).toNumber();
    }
    // Keep both the sensor value and queue count readable in the narrow header.
    function header(dc, label, compactLabel, value, pending, width) {
        var suffix = pending > 0 ? " +"+pending.toString() : "";
        var result = label+" "+value+suffix;
        if (dc.getTextWidthInPixels(result,Graphics.FONT_XTINY) <= width) { return result; }
        result = compactLabel+" "+value+suffix;
        if (dc.getTextWidthInPixels(result,Graphics.FONT_XTINY) <= width) { return result; }
        return compactLabel+value+(pending > 0 ? "+"+pending.toString() : "");
    }
    function trim(value) {
        while (value.length() > 0 && value.substring(0,1).equals(" ")) { value = value.substring(1,value.length()); }
        while (value.length() > 0 && value.substring(value.length()-1,value.length()).equals(" ")) { value = value.substring(0,value.length()-1); }
        return value;
    }
    function normalize(value) {
        var result = "";
        for (var i = 0; i < value.length(); i++) {
            var c = value.substring(i,i+1);
            result += c.equals("\n") || c.equals("\r") || c.equals("\t") ? " " : c;
        }
        return trim(result);
    }
    function ellipsis(dc, value, font, width) {
        if (dc.getTextWidthInPixels(value,font) <= width) { return value; }
        var suffix = "…";
        if (dc.getTextWidthInPixels(suffix,font) > width) { return ""; }
        while (value.length() > 0 && dc.getTextWidthInPixels(value+suffix,font) > width) { value = value.substring(0,value.length()-1); }
        return trim(value)+suffix;
    }
    // Prefer a word boundary; a single oversized token can still span both rows.
    function prefix(dc, value, font, width) {
        var count = 0; var space = 0;
        while (count < value.length() && dc.getTextWidthInPixels(value.substring(0,count+1),font) <= width) {
            count += 1;
            if (value.substring(count-1,count).equals(" ")) { space = count; }
        }
        if (count < value.length() && space > 0) { count = space; }
        return count;
    }
    function title(dc, name, w, h, layout) {
        name = normalize(name);
        var top = layout["titleTop"]; var bottom = layout["titleBottom"];
        var font = Graphics.FONT_SMALL;
        var height = dc.getFontHeight(font);
        var y = top+(bottom-top-height)/2;
        var width = roundWidth(w,h,y,height);
        if (height <= bottom-top && dc.getTextWidthInPixels(name,font) <= width) {
            return {"font"=>font,"rows"=>[[name,y,width]]};
        }
        font = Graphics.FONT_XTINY; height = dc.getFontHeight(font);
        y = top+(bottom-top-height)/2; width = roundWidth(w,h,y,height);
        if (dc.getTextWidthInPixels(name,font) <= width) { return {"font"=>font,"rows"=>[[name,y,width]]}; }
        width = roundWidth(w,h,top,height);
        var count = prefix(dc,name,font,width);
        var first = trim(name.substring(0,count));
        var remaining = trim(name.substring(count,name.length()));
        var secondY = bottom-height;
        var secondWidth = roundWidth(w,h,secondY,height);
        return {"font"=>font,"rows"=>[[first,top,width],[ellipsis(dc,remaining,font,secondWidth),secondY,secondWidth]]};
    }
}
