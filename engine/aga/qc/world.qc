/* SPDX-License-Identifier: GPL-2.0-or-later
 * AmiWind scene-walk rules. No original Quake game rules or assets.
 */
void(entity e, vector o) setorigin = #2;
void(entity e, string m) setmodel = #3;
void(entity e, vector low, vector high) setsize = #4;
entity(entity start, .string fld, string match) find = #18;
string(string modelname) precache_model = #20;
void(float style, string value) lightstyle = #35;
void(entity e) makestatic = #69;
void(entity e, float channel, string sample, float volume, float attenuation) sound = #8;
void(vector a, vector b, float nomonsters, entity ignore) traceline = #16;
float(vector value) vlen = #12;
void(vector angle) makevectors = #1;
string(string name) precache_sound = #19;
void(entity client, string name, string separator, string text) centerprint = #73;
float() droptofloor = #34;
float(vector value) vectoyaw = #13;
void(vector position, string sample, float volume, float attenuation) ambientsound = #74;
void() changeyaw = #49;
float(float value) floor = #36;
.string aw_hull;
.float aw_hand_idle;
.float aw_eye_height;
.float aw_hand_draw;
.float aw_hand_lower;
.float aw_hand_punch;
.float aw_hand_state;
.float aw_hand_goal;
.float aw_hand_started;
.float aw_attack_latched;
void(float state) aw_hand_begin = {
    self.aw_hand_state = state;
    self.aw_hand_started = time;
};
void() aw_hands_update = {
    local float elapsed, duration, first, count;
    if (self.impulse == 202) {
        self.impulse = 0;
        self.aw_hand_goal = 1 - self.aw_hand_goal;
    }
    if (self.aw_hand_state == 0 && self.aw_hand_goal) aw_hand_begin(1);
    if (self.aw_hand_state == 2 && !self.aw_hand_goal) aw_hand_begin(4);
    if (!self.button0) self.aw_attack_latched = 0;
    if (self.button0 && !self.aw_attack_latched) {
        self.aw_attack_latched = 1;
        if (self.aw_hand_state == 2) aw_hand_begin(3);
    }
    if (self.aw_hand_state == 0) { self.weaponmodel = ""; return; }
    self.weaponmodel = "progs/v_nord.mdl";
    elapsed = time - self.aw_hand_started;
    if (self.aw_hand_state == 1) { first = 8; count = 6; duration = world.aw_hand_draw; }
    if (self.aw_hand_state == 2) { first = 0; count = 8; duration = world.aw_hand_idle; }
    if (self.aw_hand_state == 3) { first = 18; count = 10; duration = world.aw_hand_punch; }
    if (self.aw_hand_state == 4) { first = 14; count = 4; duration = world.aw_hand_lower; }
    if (duration <= 0) { self.weaponmodel = ""; return; }
    if (elapsed >= duration) {
        if (self.aw_hand_state == 4) { aw_hand_begin(0); self.weaponmodel = ""; return; }
        aw_hand_begin(2); first = 0; elapsed = 0; count = 8; duration = world.aw_hand_idle;
    }
    self.weaponframe = first + floor(elapsed * count / duration);
};
.string aw_voice;
.string aw_line;
.float aw_idle_step;
.float aw_intro_role;
.float aw_ref;
.float aw_story_hidden;
.float aw_walk_step;
.float aw_moving;
.float aw_volume;
.float aw_attenuation;
.float aw_next_pose;
.float aw_next_poll;
.float aw_hello_distance;
.float aw_hello_reset;
.float aw_greet_duration;
.float aw_hello_done;
.float aw_hello_polls;
.float aw_face_until;
.float aw_hello_count;
.float aw_manual_count;
float aw_voice_deadline;
entity aw_player;
/* Small independent scene policy, not a full original dialogue evaluator. */
void(entity npc, entity listener, float automatic) aw_greet = {
    sound(npc,2,npc.aw_voice,0.9,1);
    centerprint(listener,npc.netname,"\n",npc.aw_line);
    npc.aw_hello_done = 1;
    npc.aw_hello_polls = 0;
    npc.aw_face_until = time + npc.aw_greet_duration;
    if (automatic) {
        npc.aw_hello_count = npc.aw_hello_count + 1;
        aw_voice_deadline = time + 8;
    } else {
        npc.aw_manual_count = npc.aw_manual_count + 1;
        aw_voice_deadline = time + 4;
    }
};
void() aw_npc_idle = {
    local vector delta;
    local float distance;
    self.nextthink = time + 0.125;
    if (!self.aw_moving && time >= self.aw_next_pose) {
        self.frame = self.frame + 1;
        if (self.frame >= 8) self.frame = 0;
        self.aw_next_pose = time + self.aw_idle_step;
    }
    if (aw_player == world || self.aw_intro_role) return;
    delta = aw_player.origin - self.origin;
    if (time < self.aw_face_until) {
        /* Converted NIF characters face local +Y; Quake yaw zero is +X. */
        self.ideal_yaw = vectoyaw(delta) - 90;
        if (self.ideal_yaw < 0) self.ideal_yaw = self.ideal_yaw + 360;
        changeyaw();
    }
    if (time < self.aw_next_poll) return;
    self.aw_next_poll = time + 0.25;
    distance = vlen(delta);
    if (distance >= self.aw_hello_reset && distance >= self.aw_hello_distance)
        self.aw_hello_done = 0;
    if (self.aw_hello_done || self.aw_hello_distance <= 0 ||
        distance >= self.aw_hello_distance || aw_player.health <= 0 ||
        aw_player.movetype != 3 || aw_player.waterlevel >= 2) {
        self.aw_hello_polls = 0;
        return;
    }
    /* Distance/state rejection precedes the more expensive visibility trace. */
    traceline(self.origin + '0 0 27',aw_player.origin + aw_player.view_ofs,1,self);
    if (trace_fraction < 1) { self.aw_hello_polls = 0; return; }
    self.aw_hello_polls = self.aw_hello_polls + 1;
    if (self.aw_hello_polls >= 2 && time >= aw_voice_deadline)
        aw_greet(self,aw_player,1);
};
/* All static brushes must be linked before the actor's floor trace. Exported
 * entity order is not a collision guarantee: the port platform may spawn last. */
void() aw_npc_floor = {
    local vector authored;
    authored=self.origin;
    setorigin(self,self.origin + '0 0 8');
    if (!droptofloor() || authored_z-self.origin_z>8) setorigin(self,authored);
    setorigin(self,self.origin + '0 0 0.25');
    self.solid = 3;
    setsize(self,'-7.32 -7.12 0','7.32 7.12 33.25');
    self.think = aw_npc_idle;
    self.aw_next_pose = time + self.aw_idle_step;
    self.nextthink = time + self.aw_idle_step;
};
void() aw_npc = {
    precache_model(self.model);
    if (self.aw_voice != "") precache_sound(self.aw_voice);
    self.movetype = 0;
    self.solid = 0;
    setmodel(self,self.model);
    setsize(self,'0 0 0','0 0 0');
    self.think = aw_npc_idle;
    self.yaw_speed = 22.5;
    self.aw_next_pose = time + self.aw_idle_step;
    self.nextthink = time + self.aw_idle_step;
    self.think = aw_npc_floor;
    self.nextthink = time + 0.1;
};
/* Authored dead residents keep the sampled final death pose and never greet. */
void() aw_corpse = {
    precache_model(self.model);
    self.movetype = 0;
    self.solid = 0;
    setmodel(self,self.model);
    setsize(self,'0 0 0','0 0 0');
    self.frame = 0;
};
void() aw_interact = {
    local entity npc;
    local vector eye;
    if (self.movetype != 3 || time < aw_voice_deadline) return;
    makevectors(self.v_angle);
    eye = self.origin + self.view_ofs;
    traceline(eye,eye + v_forward * 72,0,self);
    npc = trace_ent;
    if (trace_fraction >= 1 || npc == world) return;
    if (npc.classname == "aw_npc" && !npc.aw_intro_role && npc.aw_voice != "")
        aw_greet(npc,self,0);
};
void() worldspawn = {
    precache_model("progs/player.mdl");
    precache_model("progs/v_nord.mdl");
    lightstyle(0,"m");
};
void() aw_static = {
    precache_model(self.model);
    self.movetype = 0;
    self.solid = 0;
    setmodel(self,self.model);
    makestatic(self);
};
void() aw_loop = {
    precache_sound(self.aw_voice);
    ambientsound(self.origin,self.aw_voice,self.aw_volume,self.aw_attenuation);
};
void() func_wall = {
    self.movetype = 7;
    self.solid = 4;
    setmodel(self,self.model);
    setorigin(self,self.origin);
};
void() info_player_start = {};
void() StartFrame = {};
void() PlayerPostThink = {};
void() ClientKill = {};
void() ClientConnect = {};
void() ClientDisconnect = {};
void() SetNewParms = {};
void() SetChangeParms = {};
void() main = {};
void() PutClientInServer = {
    local entity start;
    start = find(world,classname,"info_player_start");
    self.movetype = 3;
    self.solid = 3;
    self.flags = 8;
    self.health = 100;
    self.view_ofs = '0 0 13.3';
    if (world.aw_eye_height > 0) self.view_ofs_z = world.aw_eye_height;
    setmodel(self,"progs/player.mdl");
    setsize(self,'-7.32 -7.12 -16.625','7.32 7.12 16.625');
    setorigin(self,start.origin);
    self.angles = start.angles;
    self.fixangle = 1;
    aw_player = self;
};
void() PlayerPreThink = {
    if (self.impulse == 201) { self.impulse = 0; aw_interact(); }
    aw_hands_update();
    if (self.button2) {
        if (self.waterlevel >= 2) self.velocity_z = 140;
        else if (self.flags & 512) {
            self.velocity_z = 150;
            self.flags = self.flags - 512;
        }
    }
};
