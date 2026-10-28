import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import pair_policy as p


class PairPolicyTests(unittest.TestCase):
    def setUp(self):
        self.selection={'source_rule':'s','target_rule':'t','direction':'first','generic_rules':['s','t','other'],
                        'order':['global','s','t','other'],'source':{'id':'wireguard:peer_1'},'target':{'id':'openvpn:1_1'}}

    def test_manual_direction_preserves_every_unrelated_policy_position(self):
        identity=p.proof(self.selection)
        self.assertEqual(p.desired_order(identity,self.selection['order'],'target'),['global','t','s','other'])
        self.assertEqual(self.selection['order'],['global','s','t','other'])

    def test_unknown_highest_generic_is_not_guessed_from_pair_health_or_relative_order(self):
        chosen=copy.deepcopy(self.selection);chosen['order']=['global','other','s','t']
        with self.assertRaisesRegex(ValueError,'PAIR-POLICY-UNVERIFIED'):p.role(p.proof(chosen),chosen['order'])

    def test_journal_cannot_authorize_movement_of_foreign_policies(self):
        before=self.selection['order'];context=p.transition(self.selection,before,'target')
        journal={'before':before,'after':['global','t','s','other'],'source':'wireguard:peer_1','target':'openvpn:1_1','pair_transition':context}
        self.assertEqual(p.metadata(journal),context)
        for key in ('primary_order','session_order'):
            changed=copy.deepcopy(journal);changed['pair_transition'][key]=['global','s','other','t']
            with self.assertRaises(ValueError):p.metadata(changed)
        changed=copy.deepcopy(journal);changed['after']=['global','t','other','s']
        with self.assertRaises(ValueError):p.metadata(changed)

    def test_foreign_active_journal_cannot_authorize_a_new_manual_command(self):
        state={'order':self.selection['order'],'policy_hash':'h','policy_roles':p.proof(self.selection)}
        self.assertFalse(p.state_order_matches(state,{'phase':'COMMITTED'},(state['order'],'h')))
        self.assertTrue(p.state_order_matches(state,{'phase':'ROLLED-BACK'},(state['order'],'h')))

    def test_bad_order_types_are_a_coded_refusal(self):
        for order in (None,[],['s',['t']],['s','s']):
            with self.assertRaises(ValueError):p.validate(p.proof(self.selection),order)


if __name__=='__main__':unittest.main()
