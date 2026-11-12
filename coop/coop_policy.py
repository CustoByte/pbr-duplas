"""Coop ownership contract, independent of UI hooks (not a playable coop mode).

Confirmed: two picks each, first pick each active, each controls own Pokemon;
survivor controls both remaining actives if the partner loses both Pokemon.
"""
from dataclasses import dataclass,field

MENU,DRAFT,ACTION,TARGET,SWITCH,REPLACEMENT=range(6)

@dataclass
class CoopPolicy:
    selection:tuple
    owners:tuple=(0,1,0,1)
    active:list=field(default_factory=lambda:[0,1])
    vacant_owner:list=field(default_factory=lambda:[0,1])
    alive:list=field(default_factory=lambda:[True]*4)
    phase:int=MENU
    owner:int=0
    epoch:int=0

    @classmethod
    def selected(cls,p1,p2):
        p1,p2=tuple(p1),tuple(p2)
        if len(p1)!=2 or len(p2)!=2:raise ValueError('Each player must select two Pokemon')
        chosen=p1+p2
        if len(set(chosen))!=4 or any(not isinstance(s,int) or not 0<=s<6 for s in chosen):
            raise ValueError('Four different slots from the shared six-Pokemon pass required')
        return cls((p1[0],p2[0],p1[1],p2[1]))

    def begin_choice(self,phase,owner):
        if phase not in(DRAFT,ACTION,TARGET,SWITCH,REPLACEMENT) or owner not in(0,1):raise ValueError('Invalid choice')
        self.phase,self.owner=phase,owner;self.epoch+=1

    def command_owner(self,position):
        if position not in(0,1):raise ValueError('Invalid active position')
        index=self.active[position]
        return None if index is None or not self.alive[index] else self.owners[index]

    def begin_command(self,position,phase=ACTION):
        if phase not in(ACTION,TARGET,SWITCH):raise ValueError('Invalid command phase')
        owner=self.command_owner(position)
        if owner is None:raise ValueError('No living active Pokemon in this position')
        self.begin_choice(phase,owner)

    def switches(self,position,player):
        if self.command_owner(position)!=player:return ()
        return tuple(i for i in range(4) if self.owners[i]==player and self.alive[i] and i not in self.active)

    def switch(self,position,index,player):
        if index not in self.switches(position,player):raise ValueError('Cannot switch another player\'s Pokemon or an invalid reserve')
        self.active[position]=index

    def faint(self,index):
        if index not in range(4):raise ValueError('Invalid Pokemon')
        self.alive[index]=False
        for position,active in enumerate(self.active):
            if active==index:
                self.vacant_owner[position]=self.owners[index]
                self.active[position]=None

    def replacements(self,position):
        if position not in(0,1) or self.active[position] is not None:
            raise ValueError('Replacement requires a vacant position')
        previous_owner=self.vacant_owner[position]
        remaining={self.owners[i] for i in range(4) if self.alive[i]}
        allowed={previous_owner} if previous_owner in remaining else remaining
        return tuple(i for i in range(4) if self.alive[i] and i not in self.active and self.owners[i] in allowed)

    def replace(self,position,index,player):
        if index not in self.replacements(position) or self.owners[index]!=player:
            raise ValueError('Only the owner can choose a valid replacement')
        self.active[position]=index
        self.vacant_owner[position]=player

    def finish(self):
        self.phase,self.owner=MENU,0;self.epoch+=1

    def can_control(self,player):return player==(0 if self.phase==MENU else self.owner)
