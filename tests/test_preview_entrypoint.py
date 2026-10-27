import os,runpy,unittest
from unittest.mock import patch
class PreviewEntrypointTests(unittest.TestCase):
 def test_preview_only_and_shared_configured_signer(self):
  for environment,enabled in [('preview',True),('production',False),('development',False)]:
   with self.subTest(environment=environment),patch.dict(os.environ,{'WW_GG_SECRET_KEY':'1'*64,'VERCEL_ENV':environment}):
    app=runpy.run_path('wsgi.py')['app']
    self.assertEqual(app.config.get('BROWSER_HISTORY_PREVIEW',False),enabled)
    self.assertEqual(app.config['SECRET_KEY'],'1'*64)
    self.assertEqual(app.config['GAME_TREE_PREVIEW'],enabled)
