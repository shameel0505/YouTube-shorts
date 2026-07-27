import os

def format_time(seconds: float) -> str:
    """Format seconds into ASS timestamp format: h:mm:ss.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def generate_ass(captions: list[dict], output_path: str, width: int = 720, height: int = 1280):
    """
    Generates an Advanced SubStation Alpha (.ass) file from Whisper captions.
    Uses discrete events for each word highlight to mimic the modern TikTok aesthetic perfectly.
    """
    # ASS Colors are BGR in hex: &H00BBGGRR&
    # We want a modern Cyan highlight (#00FFFF -> BGR: FFFF00)
    # Let's use a highly aesthetic Gold/Cyan. We'll use Cyan: &H00FFFF00& 
    # Wait, pure cyan is #00E5FF -> BGR is FF E5 00 -> &H00FFE500&
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat ExtraBold,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H88000000,0,0,0,0,100,100,1,0,1,1,4,2,60,60,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    
    for chunk in captions:
        words = chunk["words"]
        if not words:
            continue
            
        chunk_start = chunk["start"]
        chunk_end = chunk["end"]
        
        # We generate one discrete event for EACH word highlight state.
        for i, active_word in enumerate(words):
            start_t = active_word["start"]
            
            # The end of this highlight state is the start of the next word,
            # or the end of the chunk if it's the last word.
            if i < len(words) - 1:
                end_t = words[i+1]["start"]
            else:
                end_t = chunk_end
                
            # Formatting the text string
            # We use {\c&H00FFE500&} to change color to Cyan for the active word
            # and {\c&H00FFFFFF&} for inactive words.
            text_parts = []
            for j, w in enumerate(words):
                word_text = w["text"].upper().strip()
                if j == i:
                    # Highlighted word
                    text_parts.append(f"{{\\c&H00FFE500&}}{word_text}{{\\c&H00FFFFFF&}}")
                else:
                    # Inactive word
                    text_parts.append(word_text)
                    
            event_text = " ".join(text_parts)
            
            # Format: Dialogue: 0,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
            event = f"Dialogue: 0,{format_time(start_t)},{format_time(end_t)},Default,,0,0,0,,{event_text}"
            events.append(event)
            
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\\n".join(events))
        f.write("\\n")
