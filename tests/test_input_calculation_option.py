import unittest,re
from app import create_app

class InputCalculationOptionTests(unittest.TestCase):
 def setUp(self):self.c=create_app({'TESTING':True,'SECRET_KEY':'input-display-only','HYBRID_TABLE_PREVIEW':True}).test_client()
 def test_top_and_main_use_one_compact_default_off_external_display_control(self):
  top=self.c.get('/').get_data(as_text=True)
  self.c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'random','night':'random','win_cutoff':'0'})
  main=self.c.get('/main').get_data(as_text=True)
  for html in (top,main):
   controls=re.findall(r'<input[^>]*id="display-input-calculation"[^>]*>',html)
   self.assertEqual(len(controls),1);self.assertNotIn('checked',controls[0]);self.assertIn('form="display-options-form"',controls[0])
   self.assertIn('入力中に計算を進める',html)
   self.assertNotIn('重い配役では',html)
 def test_help_bookshelf_operations_display_and_explanation(self):
  html=self.c.get('/help/operations/display').get_data(as_text=True)
  self.assertIn('操作説明',html);self.assertIn('data-book="operations-display"',html)
  for text in ('入力中に計算を進める','初期設定はOff','180ms','待機中・実行中','「更新」'):self.assertIn(text,html)
