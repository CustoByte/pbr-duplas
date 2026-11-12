import itertools,unittest
from coop_policy import CoopPolicy,MENU,ACTION,TARGET,SWITCH

class PolicyTests(unittest.TestCase):
    def test_all_shared_pass_pick_orders(self):
        for order in itertools.permutations(range(6),4):
            c=CoopPolicy.selected(order[:2],order[2:])
            self.assertEqual(c.selection,(order[0],order[2],order[1],order[3]))
            self.assertEqual([c.command_owner(i) for i in(0,1)],[0,1])
            self.assertEqual(c.switches(0,0),(2,));self.assertEqual(c.switches(1,1),(3,))
            self.assertEqual(c.switches(0,1),());self.assertEqual(c.switches(1,0),())
    def test_duplicate_or_excess_picks_rejected(self):
        for p1,p2 in [((0,1),(1,2)),((0,),(2,3)),((0,1),(2,3,4)),((0,6),(2,3))]:
            with self.assertRaises(ValueError):CoopPolicy.selected(p1,p2)
    def test_first_faint_preserves_ownership_and_rejects_stealing(self):
        c=CoopPolicy.selected((0,1),(2,3));c.faint(0)
        self.assertEqual(c.replacements(0),(2,))
        with self.assertRaises(ValueError):c.replace(0,3,1)
        c.replace(0,2,0);self.assertEqual(c.command_owner(0),0)
    def test_survivor_controls_both_actives_in_both_directions(self):
        for lost in(0,1):
            c=CoopPolicy.selected((0,1),(2,3));c.faint(lost)
            reserve=lost+2;c.replace(lost,reserve,lost);c.faint(reserve)
            other=1-lost;other_reserve=other+2
            self.assertEqual(c.replacements(lost),(other_reserve,))
            c.replace(lost,other_reserve,other)
            self.assertEqual([c.command_owner(p) for p in(0,1)],[other,other])
            c.begin_command(0);first=c.epoch;c.begin_command(1)
            self.assertEqual(c.owner,other);self.assertEqual(c.epoch,first+1)
            self.assertFalse(c.can_control(lost));self.assertTrue(c.can_control(other))
    def test_fainting_after_takeover_does_not_restore_old_owner(self):
        c=CoopPolicy.selected((0,1),(2,3));c.faint(0);c.replace(0,2,0);c.faint(2);c.replace(0,3,1);c.faint(3)
        self.assertEqual(c.replacements(0),());self.assertIsNone(c.command_owner(0));self.assertEqual(c.command_owner(1),1)
    def test_only_own_living_reserve_can_switch(self):
        c=CoopPolicy.selected((0,1),(2,3))
        for target,player in[(1,0),(3,0),(2,1),(0,0)]:
            with self.assertRaises(ValueError):c.switch(0,target,player)
        c.switch(0,2,0);self.assertEqual(c.active,[2,1]);self.assertEqual(c.switches(0,0),(0,))
    def test_phase_change_is_a_new_epoch_and_menus_belong_to_p1(self):
        c=CoopPolicy.selected((0,1),(2,3));self.assertTrue(c.can_control(0));self.assertFalse(c.can_control(1))
        for phase in(ACTION,TARGET,SWITCH):c.begin_command(1,phase);self.assertEqual(c.owner,1)
        self.assertEqual(c.epoch,3);c.finish();self.assertEqual((c.phase,c.owner,c.epoch),(MENU,0,4))
    def test_no_commands_for_fainted_slots(self):
        c=CoopPolicy.selected((0,1),(2,3));c.faint(0)
        with self.assertRaises(ValueError):c.begin_command(0)

if __name__=='__main__':unittest.main()
