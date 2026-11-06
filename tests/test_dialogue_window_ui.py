# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue window's screen and keys (v0.0.61): the player's chosen answer as the player's line, the
disposition after a result script, the keyboard panes, the black backdrop and the messages over the window.
The engine wiring is checked in the source; the policy parts run natively in tests/aga_modal_world_test.c
(the backdrop) and tests/aga_hud_test.c (no status bars behind the window)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def body(text, start):
    """The function that starts with START, to its closing brace at column 0."""
    i = text.index(start)
    return text[i:text.index('\n}', i) + 2]


class ChoiceLine(unittest.TestCase):
    def test_chosen_answer_is_a_heading_and_no_empty_heading_follows(self):
        # DIALOGUE-CHOICE-LINE-UNMARKED-60: the answer the player picks from a Choice gets the same heading bar as a
        # picked topic's name; the NPC's reply follows under it without an empty heading of its own
        ask = body(code('aw_dialwin.c'), 'static void ask(int r){')
        self.assertIn('append(choice_text[k],1);', ask)
        self.assertNotIn('append(choice_text[k],0);', ask)
        self.assertIn('answer_of(topic,"")', ask)
        answer = body(code('aw_dialwin.c'), 'static void answer_with(int topic,int answer,const char *heading,int journal){')
        self.assertIn('if(heading && *heading)append(heading,1);', answer)
        self.assertIn('if(name[0])append(name,1);', answer)


class Disposition(unittest.TestCase):
    def test_script_change_is_followed_as_openmw_update_original_disposition(self):
        # DIALOGUE-RING-DISPOSITION-CHECK-60: a result's ModDisposition (Fargoth's +50 for the ring) changes the
        # speaker's own disposition; the conversation's bar follows it (OpenMW DialogueManager::
        # updateOriginalDisposition), persuasion writes the current one (setBaseDisposition), Goodbye syncs first
        win = code('aw_dialwin.c')
        sync = body(win, 'static void disposition_sync(void){')
        self.assertIn('AW_MwscriptSpeakerDisposition(speaker_record,speaker_reference,current_base)', sync)
        self.assertIn('if(live!=current_base)original_base=current_base=live;', sync)
        self.assertIn('disposition_sync();\n    facts.base=current_base;', body(win, 'static void dispose(void){'))
        persuade = body(win, 'static void persuade(int kind){')
        self.assertLess(persuade.index('disposition_sync();'), persuade.index('current_base+=r.temp;'))
        self.assertLess(persuade.index('current_base+=r.temp;'),
                        persuade.index('AW_MwscriptSetSpeakerDisposition(speaker_record,speaker_reference,current_base);'))
        goodbye = body(win, 'static void goodbye(void){')
        self.assertLess(goodbye.index('disposition_sync();'), goodbye.index('zero=AW_DialDisposition'))
        self.assertIn('AW_MwscriptSetSpeakerDisposition(speaker_record,speaker_reference,v);', goodbye)
        # the result script runs before the bar is worked out again
        result = body(win, 'static void run_result(int answer,int topic){')
        self.assertLess(result.index('AW_MwscriptRunResult('), result.index('dispose();'))
        host = code('aw_mwhost.c')
        live = body(host, 'int AW_MwscriptSpeakerDisposition(')
        self.assertIn('AW_ActorStat(disposition_restore(a),AWA_DISPOSITION)', live)
        self.assertIn('return disposition_kept(reference,fallback);', live)
        self.assertIn('disposition_keep(a);', body(host, 'void AW_MwscriptSetSpeakerDisposition('))


class Keys(unittest.TestCase):
    def test_up_down_work_in_the_focused_pane_and_tab_switches_it(self):
        # DIALOGUE-ARROWS-MOVE-POINTER-60: Up/Down move the highlighted topic or answer and Enter picks it; Tab moves
        # the keys to the conversation, where Up/Down scroll it and Left/Right choose a link for Enter
        key = body(code('aw_dialwin.c'), 'static int key(int k,int mouse_x,int mouse_y){')
        up = key[key.index('case K_UPARROW:'):key.index('case K_DOWNARROW:')]
        self.assertIn('if(pane==PANE_TEXT){scroll++;', up)
        self.assertIn('AW_ListBoxKey(&box,AW_LBKEY_UP)', up)
        down = key[key.index('case K_DOWNARROW:'):key.index('case K_TAB:')]
        self.assertIn('if(pane==PANE_TEXT){scroll--;', down)
        self.assertIn('AW_ListBoxKey(&box,AW_LBKEY_DOWN)', down)
        self.assertIn('case K_TAB:pane=pane==PANE_TEXT?PANE_LIST:PANE_TEXT;focus=-1;return 1;', key)
        side = key[key.index('case K_LEFTARROW:case K_RIGHTARROW:'):key.index('case K_ENTER:')]
        self.assertLess(side.index('if(pane==PANE_TEXT){'), side.index('if(mode==7)'))
        enter = key[key.index('case K_ENTER:'):key.index('case K_MWHEELUP:')]
        self.assertIn('if(pane==PANE_TEXT)return 1;', enter)
        self.assertIn('AW_ListBoxKey(&box,AW_LBKEY_CHOOSE)', enter)
        # typing searches the topics (back to the list); a click on the list gives it the keys
        self.assertIn('pane=PANE_LIST;focus=-1;AW_ListBoxType(&box,k);', key)
        self.assertIn('pane=PANE_LIST;focus=-1;r=AW_ListBoxClick(', key)
        # a conversation opens with the keys on the list; the focused pane is framed, the highlight dims without it
        win = code('aw_dialwin.c')
        self.assertIn('scroll=0;pane=PANE_LIST;', body(win, 'int AW_DialWindowOpen('))
        draw = body(win, 'static void draw(void){')
        self.assertIn('int x0=pane==PANE_TEXT?', draw)
        self.assertIn('pane==PANE_LIST?pick:', draw)


class Layers(unittest.TestCase):
    def test_black_backdrop_without_the_hud(self):
        # DIALOGUE-BACKDROP-HUD-60: the window's hook, the world not rendered under it, no status bars behind it
        self.assertIn('aw_ui_dialogue_backdrop=AW_DialWindowActive;', body(code('aw_dialwin.c'), 'void AW_DialWindowInit(void){'))
        hidden = body(code('aw_ui.c'), 'int AW_ModalWorldHidden(void) {')
        self.assertLess(hidden.index('aw_ui_dialogue_backdrop && aw_ui_dialogue_backdrop()'),
                        hidden.index('return (AW_InventoryActive() || AW_ModalBlackBackground())'))
        sbar = body(code('aw_hud.c'), 'void Sbar_Draw(void) {')
        guard = sbar.index('if(!(aw_ui_dialogue_backdrop && aw_ui_dialogue_backdrop())){')
        self.assertLess(guard, sbar.index('AW_UIHud();'))
        self.assertLess(guard, sbar.index('compass();'))

    def test_messages_drawn_over_the_windows(self):
        # DIALOGUE-MSGBOX-BEHIND-60: the notices and a script's message box are the top layer: after the container
        # strip (AW_IntroDraw) in play, after the world windows (M_Draw) while one is open
        update = body(code('screen.c'), 'void SCR_UpdateScreen (void)')
        self.assertLess(update.index('AW_IntroDraw();'), update.index('AW_UIDraw();'))
        self.assertLess(update.index('over_window = AW_WorldUIActive ();'), update.index('AW_UIDraw();'))
        after = update[update.index('M_Draw ();'):]
        self.assertIn('if (over_window && key_dest != key_console) {', after)
        self.assertIn('AW_UIDraw ();', after)
        self.assertIn('aw_msgbox_draw ();', after)
        # the notice box leaves the strip under the view alone while over a window or the container strip
        self.assertIn('aw_ui_over_window = over_window || (aw_cstrip_open_now && aw_cstrip_open_now ());', update)
        self.assertIn('if(centered && !aw_ui_over_window)AW_UIFill(', body(code('aw_ui.c'), 'void AW_UIDraw(void) {'))
        # a box with buttons over a world window: drawn and given its keys before the window's
        box = code('aw_msgbox.c')
        self.assertIn('return key_dest==key_game || (key_dest==key_menu && AW_WorldUIActive());', box)
        self.assertIn('if(!AW_MsgBoxActive() || !box_here())return 0;', body(box, 'int AW_MsgBoxGameKey(int key) {'))
        self.assertIn('if(!AW_MsgBoxActive() || !box_here())return;', body(box, 'void AW_MsgBoxDraw(void) {'))
        event = body(code('keys.c'), 'void Key_Event (int key, qboolean down)')
        self.assertLess(event.index('key_dest == key_menu && aw_msgbox_key && aw_msgbox_key (key)) return;'),
                        event.index('if (AW_WorldUIKey(key,down)) return;'))


class LootWindow(unittest.TestCase):
    def test_console_font_lines_properties_and_centred_pictures(self):
        # LOOT-WINDOW-LAYOUT-60 / LOOT-WINDOW-ITEM-PROPERTIES-60 (the layout itself runs natively in
        # tests/aga_container_strip_test.c and aga_container_strip_open_test.c)
        strip = code('aw_cstrip.c')
        draw = body(strip, 'void AW_CStripDraw(void){')
        self.assertIn('AW_InventoryPropertiesLine(e->id,o.text_columns,line,sizeof(line))', draw)
        self.assertIn('ctext(left,o.keys_y,', draw)
        self.assertIn('ctext(left,o.name_y,', draw)
        self.assertIn('x+(STRIP_CELL-2-iw)/2', draw)
        self.assertNotIn('Q_strcpy_bounded(line,e->name,5)', draw)   # no name cut to four letters
        self.assertIsNone(re.search(r'AW_UIText\(left,y\+11', draw))


if __name__ == '__main__':
    unittest.main()
