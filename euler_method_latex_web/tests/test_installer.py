import importlib.util
from pathlib import Path
import tempfile
import unittest

INSTALL=Path(__file__).resolve().parents[1]/'install_euler_method.py'
spec=importlib.util.spec_from_file_location('euler_installer',INSTALL)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class InstallerTests(unittest.TestCase):
    def test_add_exclude_block_keeps_original_site_config(self):
        source='title: blueink\nnav_enabled: true\n'
        fixed=m.updated_config(source,'euler_method_latex_web')
        self.assertIn('title: blueink',fixed)
        self.assertIn('nav_enabled: true',fixed)
        self.assertIn('  - euler_method_pixel_web',fixed)
        self.assertIn('  - euler_method_latex_web',fixed)
        self.assertEqual(fixed,m.updated_config(fixed,'euler_method_latex_web'))
    def test_update_existing_exclude_block(self):
        text='title: Blog\nexclude:\n  - Gemfile\nplugins:\n  - jekyll-seo-tag\n'
        fixed=m.updated_config(text,'euler_method_latex_web')
        self.assertIn('  - euler_method_pixel_web',fixed)
        self.assertIn('plugins:\n  - jekyll-seo-tag',fixed)
        self.assertEqual(fixed,m.updated_config(fixed,'euler_method_latex_web'))
    def test_updates_inline_exclude(self):
        text='exclude: [Gemfile]\nnav_order: 1\n'
        fixed=m.updated_config(text,'euler_method_latex_web')
        self.assertIn('"euler_method_pixel_web"',fixed)
        self.assertEqual(fixed,m.updated_config(fixed,'euler_method_latex_web'))
    def test_install_preserves_notes_and_only_adds_selected_files(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d)
            (r/'_config.yml').write_text('title: Example\n')
            (r/'docs/Works').mkdir(parents=True)
            (r/'docs/Works/Untexed.md').write_text('important note')
            m.install(r,INSTALL.parent)
            self.assertEqual((r/'docs/Works/Untexed.md').read_text(),'important note')
            self.assertIn('parent: Math Programs',(r/'docs/Works/Euler-Method.html').read_text())
            self.assertTrue((r/'assets/euler-method/latex.mjs').is_file())
            self.assertFalse((r/'README.md').exists())
            self.assertIn('euler_method_pixel_web',(r/'_config.yml').read_text())

if __name__=='__main__':unittest.main()
