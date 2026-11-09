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
        pick = body(code('aw_dialwin.c'), 'static void pick_choice(int k){')
        self.assertIn('append(choice_text[k],1);', pick)
        self.assertNotIn('append(choice_text[k],0);', pick)
        self.assertIn('answer_with(topic,answer,"",1);', pick)
        answer = body(code('aw_dialwin.c'), 'static void answer_with(int topic,int answer,const char *heading,int journal){')
        self.assertIn('if(heading && *heading)append(heading,1);', answer)
        self.assertIn('if(name[0])append(name,1);', answer)


class Choices(unittest.TestCase):
    """DIALOGUE-CHOICES-62: a result's Choice options are rows in the conversation text, picked by a click or by
    Up/Down and Enter, never by typed letters; while they are open the list, the links, Goodbye and Escape are refused
    (OpenMW 0.51 DialogueWindow while isInChoice); the pick searches the same topic again with the Choice value and
    every other filter. The pick rules run natively in tests/aga_dial_links_test.c, the branch filters in
    tests/test_dialogue_lut.py (NativeDialogue.test_choice_branches_follow_every_filter)."""

    def test_rows_in_the_text_not_the_list(self):
        win = code('aw_dialwin.c')
        refresh = body(win, 'static void refresh(void){')
        self.assertNotIn('CODE_CHOICE(i)', refresh)                  # the list no longer holds the options
        self.assertIn('aw_worldui_panel_holds_escape=choice_count>0;', refresh)
        self.assertNotIn('CODE_CHOICE', body(win, 'static const char *label(void *ctx,int r){'))
        lines = body(win, 'static int history_lines(int draw,int first){')
        self.assertIn('for(i=0;i<choice_count;i++){', lines)
        self.assertIn('h->para=(short)AW_DIAL_HIT_CHOICE;h->span=(short)i;', lines)
        self.assertIn('if(i==choice_focus)AW_UIFill(', lines)
        # the longest option of the masters fits (docs/dialogue-choices.json: tests/test_dialogue_choices.py)
        self.assertIn('#define CHOICE_CHARS 200', win)
        self.assertIn('#define CHOICES 10', win)
        self.assertIn('if(choice_count)return 1;', body(win, 'static int greyed(int r){'))

    def test_pick_by_row_only(self):
        win = code('aw_dialwin.c')
        keys = body(win, 'static int choice_key(int k,int mouse_x,int mouse_y){')
        self.assertIn('AW_DialChoiceStep(choice_count,choice_focus,-1)', keys)
        self.assertIn('AW_DialChoiceStep(choice_count,choice_focus,1)', keys)
        self.assertIn('case K_ENTER:if(choice_focus>=0)pick_choice(choice_focus);return 1;', keys)
        self.assertIn('if((c=AW_DialChoiceAt(hits,nhits,mouse_x,mouse_y,row_h()))>=0)pick_choice(c);', keys)
        self.assertIn('default:return 1;', keys)                   # typed letters, Goodbye, Escape: nothing
        self.assertNotIn('AW_ListBoxType', keys)
        key = body(win, 'static int key(int k,int mouse_x,int mouse_y){')
        self.assertLess(key.index('if(choice_count){int c=choice_key('), key.index('switch(k){'))
        self.assertIn('if(r<0 || r>=listed || choice_count)return;', body(win, 'static void ask(int r){'))
        self.assertIn('hits[h].para<0 || goodbye_only || choice_count', body(win, 'static void ask_link(int h){'))
        # a greeting's Choice holds Escape from the moment the window opens
        self.assertIn('aw_worldui_panel_holds_escape=choice_count>0;', body(win, 'int AW_DialWindowOpen('))
        self.assertIn('choice_focus=-1;scroll=0;', body(win, 'static void result_choice('))


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
        # DIALOGUE-LINKS-62: in the text the arrows step through the links instead of scrolling (PgUp/PgDn scroll)
        up = key[key.index('case K_UPARROW:'):key.index('case K_DOWNARROW:')]
        self.assertIn('if(pane==PANE_TEXT){step_link(-1);return 1;}', up)
        self.assertIn('AW_ListBoxKey(&box,AW_LBKEY_UP)', up)
        down = key[key.index('case K_DOWNARROW:'):key.index('case K_TAB:')]
        self.assertIn('if(pane==PANE_TEXT){step_link(1);return 1;}', down)
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


class Links(unittest.TestCase):
    """DIALOGUE-LINKS-62: a word in the text is a link only to a topic of the current topic list (OpenMW
    DialogueWindow seeds its keyword search with that list); a click or Enter asks it as the list does, never after
    Goodbye or while a Choice is open; a named topic is learned only when the speaker answers it."""

    def test_only_listed_topics_are_links(self):
        win = code('aw_dialwin.c')
        self.assertIn('return link_on(p->span[k].topic)?k:-1;', body(win, 'static int span_at('))
        refresh = body(win, 'static void refresh(void){')
        # the set follows the topic list in every mode (aw_dial_links.c; the barter list too: v0.0.62-dev1)
        self.assertIn('AW_DialLinksSet(linkable,', refresh)
        self.assertLess(refresh.index('AW_DialTopicList('), refresh.index('AW_DialLinksSet(linkable,'))
        self.assertLess(refresh.index('}else{\n        int fixed=0;'), refresh.index('if(linkable){'))

    def test_click_and_enter_ask_the_topic(self):
        win = code('aw_dialwin.c')
        ask = body(win, 'static void ask_link(int h){')
        self.assertIn('goodbye_only || choice_count || !link_on(hits[h].topic)', ask)
        self.assertIn('ask_topic(hits[h].topic);', ask)
        key = body(win, 'static int key(int k,int mouse_x,int mouse_y){')
        click = key[key.index('case K_MOUSE1:'):key.index('default:')]
        self.assertIn('ask_link(h);return 1;', click)
        enter = key[key.index('case K_ENTER:'):key.index('case K_MWHEELUP:')]
        self.assertIn('if(pane==PANE_TEXT && focus>=0 && focus<nhits){ask_link(focus);return 1;}', enter)
        # the list's own choice goes the same way (ask -> ask_topic)
        self.assertIn('ask_topic(list[r]);', body(win, 'static void ask(int r){'))

    def test_focus_and_stepping(self):
        win = code('aw_dialwin.c')
        step = body(win, 'static void step_link(int dir){')
        self.assertIn('focus=dir>0?(focus+1)%nhits:(focus<=0?nhits-1:focus-1);', step)
        key = body(win, 'static int key(int k,int mouse_x,int mouse_y){')
        self.assertIn('case K_TAB:pane=pane==PANE_TEXT?PANE_LIST:PANE_TEXT;focus=-1;return 1;', key)
        side = key[key.index('case K_LEFTARROW:case K_RIGHTARROW:'):key.index('case K_ENTER:')]
        self.assertIn('step_link(k==K_RIGHTARROW?1:-1)', side)
        # the focused link is drawn on a band
        self.assertIn('if(focus==nhits-1)AW_UIFill(', body(win, 'static int history_lines(int draw,int first){'))

    def test_learned_only_when_answered(self):
        win = code('aw_dialwin.c')
        self.assertIn('if(answers_topic(spans[i].topic))know(spans[i].topic);', body(win, 'static void show_answer(int answer){'))
        self.assertIn('&& answers_topic(spans[i].topic))return 0;', body(win, 'static int topic_spent(int topic){'))


class TopicColours(unittest.TestCase):
    """TOPIC-COLOURS-62: OpenMW's specific and exhausted topic colours behind one switch, on by default."""

    def test_specific_before_exhausted_and_one_switch(self):
        win = code('aw_dialwin.c')
        self.assertIn('static cvar_t topic_colours={"aw_dialogue_topic_colours","1",true};', win)
        spent = body(win, 'static int topic_spent(int topic){')
        self.assertIn('!AW_DialTopicColours()', spent)
        self.assertLess(spent.index('AW_DIAL_ENTRY_ACTOR)return TOPIC_SPECIFIC;'), spent.index('AW_DialHeardHas('))
        self.assertIn('return TOPIC_SPENT;', spent)
        self.assertIn('?topic_spent(list[i]):0', body(win, 'static void refresh(void){'))
        self.assertIn('AW_UIColor(115,128,204)', body(win, 'static void draw(void){'))
        self.assertIn('Cmd_AddCommand("aw_topic_colours",topic_colours_command);', win)
        menu = code('aw_menu.c')
        self.assertIn('case ROW_TOPICS:AW_DialTopicColoursToggle();break;', menu)
        cat = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('|ui topiccolours|aw_topic_colours|', cat)


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
        # ITEM-ICONS-MISSING-62: centred and filling the slot by the shared fit (aw_icons.c AW_IconDrawFit, tested by number
        # in aga_hud_icons_test.c), on a black slot; the house button for Take All and Close
        self.assertIn('AW_IconDrawFit(&strip->icon[c],x,y,STRIP_CELL-2,STRIP_CELL-2,', draw)
        self.assertIn('AW_IconLoadItem(&strip->icon[c],e->id)', draw)
        self.assertIn('AW_UIButton(right-STRIP_BUTTON_W,o.title_y,STRIP_BUTTON_W,STRIP_TITLE,"Close"', draw)
        self.assertNotIn('dark', draw)                                   # no dark brown slot
        self.assertNotIn('Q_strcpy_bounded(line,e->name,5)', draw)   # no name cut to four letters
        self.assertIsNone(re.search(r'AW_UIText\(left,y\+11', draw))


if __name__ == '__main__':
    unittest.main()
