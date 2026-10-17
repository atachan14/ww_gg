import unittest,json,re,copy
from unittest.mock import patch
from benchmarks.player_match_groups.extension_cases import fixture,game_of,publish
from benchmarks.player_match_groups.extension_reuse import ExtensionForecast
from werewolf.local_reuse import reuse_scope,enabled,make_public_engine
from werewolf.board_flow import BoardData
from werewolf.model_a_public import evaluate_public_game,clear_public_cache,public_cache_info
from werewolf.exact import Strategy


class LocalReuseTests(unittest.TestCase):
    def test_same_runtime_cache_separates_explicit_modes(self):
        _,game=fixture(mediums=1,day='max',night='max',fake='max')
        roles=BoardData.from_game(game).roles();seen=[]
        def spy(*args,**kwargs):
            result=make_public_engine(*args,**kwargs);seen.append(isinstance(result,ExtensionForecast));return result
        with patch('werewolf.local_reuse.make_public_engine',spy):
            with reuse_scope(False):old=roles.forecast(max_seconds=10)
            with reuse_scope(True):new=roles.forecast(max_seconds=10)
            with reuse_scope(False):again=roles.forecast(max_seconds=10)
        self.assertEqual(old,new);self.assertEqual(old,again);self.assertEqual(seen,[False,True])
        self.assertFalse(enabled())

    def test_global_complete_cache_separates_modes(self):
        _,game=fixture();roles=BoardData.from_game(game).roles();strategy=Strategy(**game['policy']);clear_public_cache()
        with reuse_scope(False):old=evaluate_public_game(game,roles.board,roles.rules,strategy,max_seconds=10)
        with reuse_scope(True):new=evaluate_public_game(game,roles.board,roles.rules,strategy,max_seconds=10)
        self.assertEqual(old,new);self.assertEqual(public_cache_info().misses,2)

    def test_stream_worker_roles_first_edit_cold_browser_and_mode_switch(self):
        client,_=fixture(mediums=1,day='max',night='max',fake='max')
        app=client.application;app.config['MANUAL_CALC_MAX_SECONDS']=10
        before=game_of(client);seen=[]
        def spy(*args,**kwargs):
            result=make_public_engine(*args,**kwargs);seen.append(isinstance(result,ExtensionForecast));return result
        def request(c):
            response=c.get('/main',headers={'Accept':'application/x-ndjson'})
            self.assertEqual(response.status_code,200)
            events=[json.loads(line)for line in response.data.decode().splitlines()]
            self.assertFalse(any(e['event']=='error'for e in events))
            events=[e for e in events if e['event']in('roles','complete')]
            self.assertEqual([e['event']for e in events],['roles','complete'])
            return [tuple(re.findall(r'data-fraction="([^"]+)"',e['html']))for e in events]
        with patch('werewolf.local_reuse.make_public_engine',spy):
            app.config['EXACT_FUTURE_REUSE_PREVIEW']=True;new=request(client)
            app.config['EXACT_FUTURE_REUSE_PREVIEW']=False;old=request(client)
        self.assertEqual(new,old);self.assertIn(True,seen);self.assertIn(False,seen)
        self.assertEqual(game_of(client),before)
        app.config['EXACT_FUTURE_REUSE_PREVIEW']=True
        publish(client,5,mediums=1);corrected=request(client)
        cookie=client.get_cookie('session');cold=app.test_client();cold.set_cookie('session',cookie.value)
        self.assertEqual(corrected,request(cold))
        self.assertFalse(enabled())

    def test_root_history_fallback_retains_original_forecast(self):
        client,game=fixture();publish(client,3,withdraw=True);game=game_of(client)
        roles=BoardData.from_game(game).roles()
        with reuse_scope(False):old=roles.forecast(max_seconds=10)
        with reuse_scope(True):new=roles.forecast(max_seconds=10)
        self.assertEqual(old,new)

    def test_hosted_cannot_enable_local_experiment(self):
        from app import create_app
        import os
        with patch.dict(os.environ,{'WW_GG_SECRET_KEY':'a'*64}):
            with self.assertRaisesRegex(ValueError,'local-only'):
                create_app({'EXACT_FUTURE_REUSE_PREVIEW':True},deployment=True)

    def test_unknown_report_shape_falls_back_without_new_certificate(self):
        from benchmarks.player_match_groups.extension_cases import prepare_game
        from werewolf.information_set_forecast import InformationSetForecast
        _,game=fixture();_,_,b,s,past,rules,strategy,_=prepare_game(game)
        with reuse_scope(True):
            engine=make_public_engine(InformationSetForecast,b,s,(object(),object()),rules,strategy)
        self.assertIs(type(engine),InformationSetForecast)
