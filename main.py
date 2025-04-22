import os
import re
from nicegui import ui, html
import uvicorn

PROCESSED_FOLDER_PATH = "/Users/jadechang/Documents/Music IC Project/processed_results_THIS/"  # Folder containing multiple processed files

scale_dialog = ui.dialog().props("persistent")  # keep it open until closed manually
with scale_dialog:
    with ui.card() as scale_card:
        scale_label_title = ui.label().classes("text-lg font-bold")
        scale_label_body = ui.label().classes("text-md")
        ui.button("Close", on_click=scale_dialog.close)

def get_processed_files():
    """Returns a list of available processed .txt files."""
    if not os.path.exists(PROCESSED_FOLDER_PATH):
        return []
    return sorted([f for f in os.listdir(PROCESSED_FOLDER_PATH) if f.endswith("_processed.txt")])

def format_chord(chord):
    """Replaces 'b' with ♭ and '#' with ♯ for proper music notation, and removes brackets."""
    return chord.replace("b", "♭").replace("#", "♯").strip("[]").strip()

def simplify_chord(chord):
    """
    Keeps root and chord quality (e.g., D7, Gm7b5), removes added tensions like b9, #11, 13.
    """
    chord = chord.replace("♭", "b").replace("♯", "#").strip()

    # Match root + quality only: e.g., "D", "Dm7", "D7", "Dmaj7", "Dm7b5"
    match = re.match(r"^([A-G][b#]?)(maj7|m7b5|m7|m|7|maj)?", chord)

    if match:
        return match.group(1) + (match.group(2) or "")
    else:
        return chord  # fallback






def extract_sections_from_content(content):
    """Extracts sections and chords from the processed file content."""
    sections = re.split(r"Section:\s*([A-Za-z0-9]+)(\n|$)", content)
    sections = [s.strip() for s in sections if s.strip()]

    main_dict = {}
    for i in range(0, len(sections), 2):
        section_name = sections[i]
        section_content = sections[i + 1]

        section_dict = {"Section Name": section_name, "Original Chords": [], "Roman Numerals": []}

        lines = section_content.splitlines()

        found_roman_numerals = False  # Flag to track when we reach Roman numeral lines
        roman_numeral_lines = []

        for line in lines:
            line = line.strip()

            # Check if this line contains Roman numerals
            if "Roman Numerals:" in line:
                found_roman_numerals = True
                continue  # Skip this line and process the next ones

            if found_roman_numerals:
                if line.strip() == "":  # Stop if we hit an empty line
                    break
                roman_numeral_lines.append(line.strip())

            # Detect chords inside square brackets
            match_chords = re.findall(r"\[(.*?)\]", line)
            if match_chords:
                cleaned_chords = [bar.replace("'", "").strip("[]").strip() for bar in match_chords]
                section_dict["Original Chords"].extend(cleaned_chords)

        # Store Roman numeral analysis
        if roman_numeral_lines:
            section_dict["Roman Numerals"] = " ".join(roman_numeral_lines).split()  # Convert to list

        main_dict[section_name] = section_dict

    return main_dict


def is_ii_v_i_progression(chord1, chord2, chord3):
    """Checks if the given three chords form a ii-V-I progression in any key."""
    ii_v_i_patterns = {
        "C": ("Dm7", "G7", "Cmaj7"), "Db": ("Ebm7", "Ab7", "Dbmaj7"),
        "D": ("Em7", "A7", "Dmaj7"), "Eb": ("Fm7", "Bb7", "Ebmaj7"),
        "E": ("F#m7", "B7", "Emaj7"), "F": ("Gm7", "C7", "Fmaj7"),
        "Gb": ("Abm7", "Db7", "Gbmaj7"), "G": ("Am7", "D7", "Gmaj7"),
        "Ab": ("Bbm7", "Eb7", "Abmaj7"), "A": ("Bm7", "E7", "Amaj7"),
        "Bb": ("Cm7", "F7", "Bbmaj7"), "B": ("C#m7", "F#7", "Bmaj7"),
    }

    for pattern in ii_v_i_patterns.values():
        if (chord1, chord2, chord3) == pattern:
            return True
    return False

def is_minor_ii_v_i_progression(chord1, chord2, chord3):
    minor_patterns = {
        "C": ("Dm7b5", "G7", "Cm"), "Db": ("Ebm7b5", "Ab7", "Dbm"),
        "D": ("Em7b5", "A7", "Dm"), "Eb": ("Fm7b5", "Bb7", "Ebm"),
        "E": ("F#m7b5", "B7", "Em"), "F": ("Gm7b5", "C7", "Fm"),
        "Gb": ("Abm7b5", "Db7", "Gbm"), "G": ("Am7b5", "D7", "Gm"),
        "Ab": ("Bbm7b5", "Eb7", "Abm"), "A": ("Bm7b5", "E7", "Am"),
        "Bb": ("Cm7b5", "F7", "Bbm"), "B": ("C#m7b5", "F#7", "Bm"),
    }
    s1, s2, s3 = simplify_chord(chord1), simplify_chord(chord2), simplify_chord(chord3)
    return any((s1, s2, s3) == pattern for pattern in minor_patterns.values())

def extract_root(chord):
    match = re.match(r"([A-G][b#]?)", chord)
    return match.group(1) if match else None

def interval_between(root1, root2):
    scale = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    # Normalize enharmonics
    def normalize(note): return note.replace("Db", "C#").replace("D#", "Eb").replace("Gb", "F#").replace("G#", "Ab").replace("A#", "Bb")
    r1 = normalize(root1)
    r2 = normalize(root2)
    i1 = scale.index(r1)
    i2 = scale.index(r2)
    interval = (i1 - i2) % 12
    return "P5" if interval == 7 else ("−4" if interval == 5 else None)

def is_secondary_dominant(chord1, chord2):
    """
    Returns True if chord1 is a dominant 7 that resolves as a secondary dominant to chord2.
    """
    # Simplify both chords
    c1 = simplify_chord(chord1)
    c2 = simplify_chord(chord2)

    # Must be dominant 7
    if not c1.endswith("7") or "maj7" in c1:
        return False

    # Extract roots
    root1 = extract_root(c1)
    root2 = extract_root(c2)

    # A secondary dominant resolves down a fifth (or up a fourth)
    interval = interval_between(root1, root2)

    return interval in ["P5", "−4"]  # fifth down or fourth up


def display_original_chords(main_dict):
    """ Displays each bar of original chords as an individual button, moving to a new row every 4 bars. """
    with ui.card().classes('p-4'):
        ui.label('Original Chords').classes('text-lg font-bold')

        for section_name, content in main_dict.items():
            ui.label(f"Section {section_name}").classes("text-xl font-semibold mt-4")

            original_chords = content.get("Original Chords", [])

            if not original_chords:
                ui.label("No chords found.").classes("text-md text-red-500")
                continue

            row = None
            for index, chord_bar in enumerate(original_chords):
                formatted_chord = format_chord(chord_bar)

                if index % 4 == 0:
                    row = ui.row().classes("gap-2 wrap")  

                with row:
                    ui.button(formatted_chord, on_click=lambda c=formatted_chord: ui.notify(f'Clicked {c}!'))  




def display_analysis(main_dict):
    with ui.card().classes('p-4'):
        ui.label('Roman Numeral Analysis').classes('text-lg font-bold')

        for section_name, content in main_dict.items():
            ui.label(f"Section {section_name}").classes("text-xl font-semibold mt-4")

            original_chords = content.get("Original Chords", [])
            roman_numerals = content.get("Roman Numerals", [])

            if not original_chords or not roman_numerals:
                ui.label("No analysis found.").classes("text-md text-red-500")
                continue

            # Detect ii–V–I and minor iiø–V–i progressions
            ii_v_i_major_indices = set()
            ii_v_i_minor_indices = set()

            for i in range(len(original_chords) - 2):
                raw1, raw2, raw3 = original_chords[i], original_chords[i+1], original_chords[i+2]
                if is_ii_v_i_progression(raw1, raw2, raw3):
                    ii_v_i_major_indices.update([i, i+1, i+2])
                elif is_minor_ii_v_i_progression(raw1, raw2, raw3):
                    ii_v_i_minor_indices.update([i, i+1, i+2])

            secondary_dom_indices = set()
            
            for i in range(len(original_chords) - 1):
                c1, c2 = original_chords[i], original_chords[i + 1]
                if is_secondary_dominant(c1, c2):
                    secondary_dom_indices.update([i, i + 1])  # highlight both the V7 and the target


            # Helper to toggle and show scale suggestions
            def handle_chord_click(btn, chord, numeral, idx, major_set, minor_set):
                toggle_chord(btn, chord, numeral)
                # if idx in major_set or idx in minor_set:
                show_scale_suggestion(chord, get_scale_suggestion(chord))

            # Render buttons
            for index in range(0, len(original_chords), 4):
                row = ui.row().classes("gap-2 wrap")
                for j in range(4):
                    idx = index + j
                    if idx >= len(original_chords):
                        break

                    raw_chord = original_chords[idx]
                    raw_numeral = roman_numerals[idx] if idx < len(roman_numerals) else raw_chord

                    display_chord = format_chord(raw_chord)
                    display_numeral = format_chord(raw_numeral)

                    if idx in ii_v_i_major_indices:
                        color = "green"
                    elif idx in ii_v_i_minor_indices:
                        color = "purple"
                    elif idx in secondary_dom_indices:
                        color = "orange"
                    else:
                        color = "blue"


                    with row:
                        tooltip_text = get_scale_suggestion(raw_chord) if idx in ii_v_i_major_indices or idx in ii_v_i_minor_indices else ""

                        btn = ui.button(display_chord, color=color).tooltip(tooltip_text)
                        btn.on("click", lambda e, b=btn, c=display_chord, n=display_numeral: toggle_chord(b, c, n))




# def show_scale_suggestion(chord, scale_info):
#     ui.label(scale_info).style("font-size: 30px; line-height: 1.5;")
#     print(f"SHOWING SUGGESTION for: {chord}")
#     scale_label_title.set_text(f"🎵 Improvisation Tips for {chord}")
#     scale_label_body.set_text(scale_info)
#     scale_dialog.open()

def show_scale_suggestion(chord, scale_info):
    formatted_text = scale_info.replace('\n', '<br>')

    with ui.dialog() as dialog, ui.card():
        ui.label(f"🎵 Improvisation Tips for {chord}").style("font-size: 22px !important; font-weight: bold; margin-bottom: 10px;")
        ui.html(f"""
            <div style='font-size: 18px !important; line-height: 1.6; color: #000;'>
                {formatted_text}
            </div>
        """)
        ui.button("Close", on_click=dialog.close)




"""

def get_scale_suggestion(chord):
    simplified = simplify_chord(chord)
    print(f"Clicked chord: {chord} → simplified: {simplified}")

    suggestions = {
        # === Major ii–V–I ===
        "Dm7": "D Dorian — from C major.",
        "G7": "G Mixolydian or G Bebop Dominant.",
        "Cmaj7": "C Ionian — base scale.",
        
        "Ebm7": "Eb Dorian — from Db major.",
        "Ab7": "Ab Mixolydian — resolve to Db.",
        "Dbmaj7": "Db Ionian — base scale.",
        
        "Em7": "E Dorian — from D major.",
        "A7": "A Mixolydian — target C#.",
        "Dmaj7": "D Ionian — base scale.",
        
        "Fm7": "F Dorian — from Eb major.",
        "Bb7": "Bb Mixolydian — target D.",
        "Ebmaj7": "Eb Ionian — base scale.",
        
        "F#m7": "F# Dorian — from E major.",
        "B7": "B Mixolydian — target D#.",
        "Emaj7": "E Ionian — base scale.",
        
        "Gm7": "G Dorian — from F major.",
        "C7": "C Mixolydian — target E.",
        "Fmaj7": "F Ionian — base scale.",
        
        "Abm7": "Ab Dorian — from Gb major.",
        "Db7": "Db Mixolydian — target F.",
        "Gbmaj7": "Gb Ionian — base scale.",
        
        "Am7": "A Dorian — from G major.",
        "D7": "D Mixolydian — target F#.",
        "Gmaj7": "G Ionian — base scale.",
        
        "Bbm7": "Bb Dorian — from Ab major.",
        "Eb7": "Eb Mixolydian — target G.",
        "Abmaj7": "Ab Ionian — base scale.",
        
        "Bm7": "B Dorian — from A major.",
        "E7": "E Mixolydian — target G#.",
        "Amaj7": "A Ionian — base scale.",
        
        "Cm7": "C Dorian — from Bb major.",
        "F7": "F Mixolydian — target A.",
        "Bbmaj7": "Bb Ionian — base scale.",
        
        "C#m7": "C# Dorian — from B major.",
        "F#7": "F# Mixolydian — target A#.",
        "Bmaj7": "B Ionian — base scale.",

        # === Minor iiø7–V7–i ===
        "Dm7b5": "D Locrian ♮2 — from C melodic minor.",
        "G7": "G Altered — from Ab melodic minor.",
        "Cm": "C Dorian or Aeolian — explore G melodic minor.",

        "Ebm7b5": "Eb Locrian ♮2 — from Db melodic minor.",
        "Ab7": "Ab Altered — from A melodic minor.",
        "Dbm": "Db Dorian or Aeolian — from Gb major or A melodic minor.",

        "Em7b5": "E Locrian ♮2 — from D melodic minor.",
        "A7": "A Altered — from Bb melodic minor.",
        "Dm": "D Dorian or Aeolian — from C or Bb major.",

        "Fm7b5": "F Locrian ♮2 — from Eb melodic minor.",
        "Bb7": "Bb Altered — from B melodic minor.",
        "Ebm": "Eb Dorian or Aeolian — try Ab major scale.",

        "F#m7b5": "F# Locrian ♮2 — from E melodic minor.",
        "B7": "B Altered — from C melodic minor.",
        "Em": "E Dorian or Aeolian — explore D or G major.",

        "Gm7b5": "G Locrian ♮2 — from F melodic minor.",
        "C7": "C Altered — from Db melodic minor.",
        "Fm": "F Dorian or Aeolian — explore Bb major.",

        "Abm7b5": "Ab Locrian ♮2 — from Gb melodic minor.",
        "Db7": "Db Altered — from D melodic minor.",
        "Gbm": "Gb Dorian or Aeolian — try B major.",

        "Am7b5": "A Locrian ♮2 — from G melodic minor.",
        "D7": "D Altered — from Eb melodic minor.",
        "Gm": "G Dorian — try F major.",

        "Bbm7b5": "Bb Locrian ♮2 — from Ab melodic minor.",
        "Eb7": "Eb Altered — from E melodic minor.",
        "Abm": "Ab Aeolian or Dorian — try Db major.",

        "Bm7b5": "B Locrian ♮2 — from A melodic minor.",
        "E7": "E Altered — from F melodic minor.",
        "Am": "A Aeolian or Dorian — from G major.",

        "Cm7b5": "C Locrian ♮2 — from Bb melodic minor.",
        "F7": "F Altered — from Gb melodic minor.",
        "Bbm": "Bb Aeolian — try Eb major.",

        "C#m7b5": "C# Locrian ♮2 — from B melodic minor.",
        "F#7": "F# Altered — from G melodic minor.",
        "Bm": "B Aeolian — from A major.",
    }

    return suggestions.get(simplified, "Try arpeggios, modes, or chromatic approaches.")

"""

def get_scale_suggestion(chord):
    simplified = simplify_chord(chord)
    print(f"Clicked chord: {chord} → simplified: {simplified}")

    suggestions = {
        # === MAJOR ii–V–I CHORDS ===
        "Dm7": "🎯 Dm7\n- Scale: D Dorian (C major)\n- Arpeggio: Dm7, Fmaj7\n- Concept: Target F and A (3rd & 5th)",
        "G7": "🎯 G7\n- Scale: G Mixolydian, Bebop Dominant\n- Arpeggio: G7, Bdim\n- Concept: Use chromatic approach to C",
        "Cmaj7": "🎯 Cmaj7\n- Scale: C Ionian\n- Arpeggio: Cmaj7, Em7\n- Concept: Voice lead 7→6→5 using B–A–G",

        "Ebm7": "🎯 Ebm7\n- Scale: Eb Dorian (Db major)\n- Arpeggio: Ebm7, Gbmaj7\n- Concept: Target Gb and Bb",
        "Ab7": "🎯 Ab7\n- Scale: Ab Mixolydian, Bebop Dominant\n- Arpeggio: Ab7, Cdim\n- Concept: Tension → resolve to Db",
        "Dbmaj7": "🎯 Dbmaj7\n- Scale: Db Ionian\n- Arpeggio: Dbmaj7, Fm7\n- Concept: Try add9 or major 6 voicings",

        "Em7": "🎯 Em7\n- Scale: E Dorian (D major)\n- Arpeggio: Em7, Gmaj7\n- Concept: Use pentatonic with color tones",
        "A7": "🎯 A7\n- Scale: A Mixolydian, Bebop Dominant\n- Arpeggio: A7, C#dim\n- Concept: Enclosure around C#",
        "Dmaj7": "🎯 Dmaj7\n- Scale: D Ionian\n- Arpeggio: Dmaj7, F#m7\n- Concept: Resolve from b9 on A7",

        "Fm7": "🎯 Fm7\n- Scale: F Dorian (Eb major)\n- Arpeggio: Fm7, Abmaj7\n- Concept: Highlight minor 6 (D)",
        "Bb7": "🎯 Bb7\n- Scale: Bb Mixolydian\n- Arpeggio: Bb7, Ddim\n- Concept: Mix of diatonic and blues scale",
        "Ebmaj7": "🎯 Ebmaj7\n- Scale: Eb Ionian\n- Arpeggio: Ebmaj7, Gm7\n- Concept: Melodic phrasing on 3–5–7",

        "F#m7": "🎯 F#m7\n- Scale: F# Dorian (E major)\n- Arpeggio: F#m7, Amaj7\n- Concept: Use minor pentatonic",
        "B7": "🎯 B7\n- Scale: B Mixolydian, Bebop Dominant\n- Arpeggio: B7, D#dim\n- Concept: Target F# and A#",
        "Emaj7": "🎯 Emaj7\n- Scale: E Ionian\n- Arpeggio: Emaj7, G#m7\n- Concept: Use rootless voicings",

        "Gm7": "🎯 Gm7\n- Scale: G Dorian (F major)\n- Arpeggio: Gm7, Bbmaj7\n- Concept: Use 9th (A) for color",
        "C7": "🎯 C7\n- Scale: C Mixolydian, Bebop Dominant\n- Arpeggio: C7, Eº\n- Concept: Blues inflection",
        "Fmaj7": "🎯 Fmaj7\n- Scale: F Ionian\n- Arpeggio: Fmaj7, Am7\n- Concept: Stepwise motion around E and G",

        "Abm7": "🎯 Abm7\n- Scale: Ab Dorian (Gb major)\n- Arpeggio: Abm7, Bmaj7\n- Concept: Combine pentatonic and dorian",
        "Db7": "🎯 Db7\n- Scale: Db Mixolydian\n- Arpeggio: Db7, Eº\n- Concept: Use approach tones to F and Ab",
        "Gbmaj7": "🎯 Gbmaj7\n- Scale: Gb Ionian\n- Arpeggio: Gbmaj7, Bbm7\n- Concept: Use open voicings",

        "Am7": "🎯 Am7\n- Scale: A Dorian (G major)\n- Arpeggio: Am7, Cmaj7\n- Concept: Use A minor pentatonic with 9",
        "D7": "🎯 D7\n- Scale: D Mixolydian, Bebop Dominant\n- Arpeggio: D7, F#dim\n- Concept: Target F# and resolve to G",
        "Gmaj7": "🎯 Gmaj7\n- Scale: G Ionian\n- Arpeggio: Gmaj7, Bm7\n- Concept: Voice lead from 7th to 6th",

        "Bbm7": "🎯 Bbm7\n- Scale: Bb Dorian (Ab major)\n- Arpeggio: Bbm7, Dbmaj7\n- Concept: Use b3 and b7 in phrasing",
        "Eb7": "🎯 Eb7\n- Scale: Eb Mixolydian\n- Arpeggio: Eb7, Gdim\n- Concept: Blues or bebop dominant lines",
        "Abmaj7": "🎯 Abmaj7\n- Scale: Ab Ionian\n- Arpeggio: Abmaj7, Cm7\n- Concept: Add 9 or 6 to sweeten the sound",

        "Bm7": "🎯 Bm7\n- Scale: B Dorian (A major)\n- Arpeggio: Bm7, Dmaj7\n- Concept: Minor pentatonic overlay",
        "E7": "🎯 E7\n- Scale: E Mixolydian\n- Arpeggio: E7, G#dim\n- Concept: Chromatic approach from F# or G",
        "Amaj7": "🎯 Amaj7\n- Scale: A Ionian\n- Arpeggio: Amaj7, C#m7\n- Concept: Emphasize major 7 and 9",

        "Cm7": "🎯 Cm7\n- Scale: C Dorian (Bb major)\n- Arpeggio: Cm7, Ebmaj7\n- Concept: Use minor triad + 9",
        "F7": "🎯 F7\n- Scale: F Mixolydian\n- Arpeggio: F7, Aº\n- Concept: Classic blues–jazz crossover",
        "Bbmaj7": "🎯 Bbmaj7\n- Scale: Bb Ionian\n- Arpeggio: Bbmaj7, Dm7\n- Concept: Use natural 9 or #11 for color",

        "C#m7": "🎯 C#m7\n- Scale: C# Dorian (B major)\n- Arpeggio: C#m7, Emaj7\n- Concept: Combine legato lines with skips",
        "F#7": "🎯 F#7\n- Scale: F# Mixolydian\n- Arpeggio: F#7, A#dim\n- Concept: Target A# and resolve to B",
        "Bmaj7": "🎯 Bmaj7\n- Scale: B Ionian\n- Arpeggio: Bmaj7, D#m7\n- Concept: Lush voicings with 9 and 13",

        # === MINOR iiø–V–i CHORDS ===
        "Dm7b5": "🎯 Dm7b5\n- Scale: D Locrian ♮2 (C melodic minor)\n- Arpeggio: Dm7b5, Fmin\n- Concept: Emphasize b5 and b7",
        "Cm": "🎯 Cm\n- Scale: C Dorian or Aeolian\n- Arpeggio: Cm7, Ebmaj7\n- Concept: Minor 6 and melodic phrasing",

        "Ebm7b5": "🎯 Ebm7b5\n- Scale: Eb Locrian ♮2 (Db melodic minor)\n- Arpeggio: Ebm7b5, Gbmin\n- Concept: Use natural 9 (F)",
        "Dbm": "🎯 Dbm\n- Scale: Db Aeolian or melodic minor\n- Arpeggio: Dbm, Fbmaj7\n- Concept: Darker modal color",

        "Em7b5": "🎯 Em7b5\n- Scale: E Locrian ♮2 (D melodic minor)\n- Arpeggio: Em7b5, Gmin\n- Concept: Voice lead b5 to 5",
        "Dm": "🎯 Dm\n- Scale: D Aeolian, D melodic minor\n- Arpeggio: Dm7, Fmaj7\n- Concept: Use 6 or 9 as tension",

        "Fm7b5": "🎯 Fm7b5\n- Scale: F Locrian ♮2 (Eb melodic minor)\n- Arpeggio: Fm7b5, Abmin\n- Concept: Outline dim7 movement",
        "Ebm": "🎯 Ebm\n- Scale: Eb Dorian or Aeolian\n- Arpeggio: Ebm7, Gbmaj7\n- Concept: Blues minor phrasing",

        "F#m7b5": "🎯 F#m7b5\n- Scale: F# Locrian ♮2 (E melodic minor)\n- Arpeggio: F#m7b5, Amin\n- Concept: Target natural 9",
        "Em": "🎯 Em\n- Scale: E Aeolian or Dorian\n- Arpeggio: Em7, Gmaj7\n- Concept: Use minor triad with passing tones",

        "Gm7b5": "🎯 Gm7b5\n- Scale: G Locrian ♮2 (F melodic minor)\n- Arpeggio: Gm7b5, Bbmin\n- Concept: Target D and F",
        "Fm": "🎯 Fm\n- Scale: F Aeolian, melodic minor\n- Arpeggio: Fm7, Abmaj7\n- Concept: Minor 6 for melodic color",

        "Abm7b5": "🎯 Abm7b5\n- Scale: Ab Locrian ♮2 (Gb melodic minor)\n- Arpeggio: Abm7b5, Bmin\n- Concept: Smooth chromaticism",
        "Gbm": "🎯 Gbm\n- Scale: Gb Aeolian or Dorian\n- Arpeggio: Gbm7, Amaj7\n- Concept: Target A and Db",

        "Am7b5": "🎯 Am7b5\n- Scale: A Locrian ♮2 (G melodic minor)\n- Arpeggio: Am7b5, Cmin\n- Concept: Connect to D7 with voice leading",
        "Gm": "🎯 Gm\n- Scale: G Dorian (F major), melodic minor\n- Arpeggio: Gm7, Bbmaj7\n- Concept: Use E (6) for modal flavor",

        "Bbm7b5": "🎯 Bbm7b5\n- Scale: Bb Locrian ♮2 (Ab melodic minor)\n- Arpeggio: Bbm7b5, Dbmin\n- Concept: Chromatic to Eb7",
        "Abm": "🎯 Abm\n- Scale: Ab Aeolian, melodic minor\n- Arpeggio: Abm7, Cbmaj7\n- Concept: Use b3→2 resolution",

        "Bm7b5": "🎯 Bm7b5\n- Scale: B Locrian ♮2 (A melodic minor)\n- Arpeggio: Bm7b5, Dmin\n- Concept: Link to E7 with half-step",
        "Am": "🎯 Am\n- Scale: A Aeolian, melodic minor\n- Arpeggio: Am7, Cmaj7\n- Concept: 6 and 9 add expressive color",

        "Cm7b5": "🎯 Cm7b5\n- Scale: C Locrian ♮2 (Bb melodic minor)\n- Arpeggio: Cm7b5, Ebmin\n- Concept: Voice lead to F7",
        "Bbm": "🎯 Bbm\n- Scale: Bb Aeolian or melodic minor\n- Arpeggio: Bbm7, Dbmaj7\n- Concept: Use chromatic grace notes",

        "C#m7b5": "🎯 C#m7b5\n- Scale: C# Locrian ♮2 (B melodic minor)\n- Arpeggio: C#m7b5, Emin\n- Concept: Connect to F#7",
        "Bm": "🎯 Bm\n- Scale: B Aeolian or Dorian\n- Arpeggio: Bm7, Dmaj7\n- Concept: Create lyrical resolution",
    }

    return suggestions.get(simplified, "🎯 Suggestions\n- Scale: Try modes or altered scales\n- Arpeggio: Use root + guide tones\n- Concept: Chromaticism, enclosures, or phrasing")




def toggle_chord(button, chord, numeral):
    """Toggles between the original chord and its Roman numeral analysis."""
    current_text = button.text
    button.set_text(numeral if current_text == chord else chord)




def display_selected_file(file_name):
    """Reads the selected processed file and updates the UI."""
    file_path = os.path.join(PROCESSED_FOLDER_PATH, file_name)

    if not os.path.exists(file_path):
        ui.notify("File not found!", color="red")
        return

    with open(file_path, "r") as file:
        content = file.read()

    # Process and display file content
    main_dict = extract_sections_from_content(content)
    update_ui_with_new_data(main_dict)

def update_ui_with_new_data(main_dict):
    """Updates the UI with new data from the selected file."""
    content_area.clear()
    with content_area:
        with ui.tabs().classes('w-full') as tabs:
            one = ui.tab('Original Chords')
            two = ui.tab('Roman Numerals')

        with ui.tab_panels(tabs, value=one).classes('w-full'):
            with ui.tab_panel(one):
                display_original_chords(main_dict)  

            with ui.tab_panel(two):
                display_analysis(main_dict)  

content_area = ui.column()

ui.label("Jazz Analysis Viewer").classes('text-2xl font-bold')

# Dropdown for file selection
selected_file = ui.select(
    options=get_processed_files(),
    with_input=True,
    on_change=lambda e: display_selected_file(e.value)
).classes('w-full')

# ui.run()

# ✅ Expose app so Uvicorn can run it:
app = ui.get_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)