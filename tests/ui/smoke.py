"""Real Chromium UI test against the real local API; uses no external accounts."""
import os
import sys
import tempfile
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from personaweave.host import Host
from personaweave.server import server
from playwright.sync_api import sync_playwright

out = Path(os.environ.get('PW_UI_OUTPUT', 'test-results'))
out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as root:
    host = Host(root)
    httpd, token = server(host)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            options = dict(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
            if os.environ.get('PW_CHROMIUM'):
                options['executable_path'] = os.environ['PW_CHROMIUM']
            browser = p.chromium.launch(**options)
            page = browser.new_page(viewport={'width': 1360, 'height': 950})
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.goto(f'http://127.0.0.1:{httpd.server_port}/#{token}')
            if os.environ.get('PW_TEST_FONT'):
                font_css = Path(os.environ['PW_TEST_FONT'])
                page.route('**/pw-test-fonts/*', lambda route: route.fulfill(path=str(font_css.parent/'files'/route.request.url.rsplit('/',1)[1]), content_type='font/woff2' if route.request.url.endswith('.woff2') else 'font/woff'))
                css = font_css.read_text().replace('./files/', '/pw-test-fonts/')
                page.add_style_tag(content=css+"body,button,input,select,textarea{font-family:'Noto Sans SC',sans-serif!important}")
                page.evaluate('document.fonts.ready')
            page.get_by_role('heading', name='与角色交谈 · 交付任务').wait_for()
            page.screenshot(path=str(out/'visual-overview-empty.png'), full_page=True)
            page.screenshot(path=str(out/'visual-overview-preview.png'))
            page.locator('nav').get_by_role('button', name='人格工坊').click()
            page.get_by_label('角色名', exact=True).fill('测试角色')
            page.get_by_label('人格文案', exact=True).fill('自由创作的人格；测试 <script> 不应执行。')
            page.get_by_label('日常引擎').select_option('openai')
            page.get_by_role('button', name='保存角色', exact=True).click()
            page.get_by_text('角色已保存。', exact=True).wait_for()
            assert len(host.store.characters()) == 1
            page.evaluate('window.scrollTo(0,0)')
            page.wait_for_timeout(150)
            page.screenshot(path=str(out/'visual-character-studio.png'), full_page=True)
            for name, heading in [('记忆与关系', '长期记忆 · 事件 · 人物关系'), ('知识文档', '角色知识库')]:
                page.locator('nav').get_by_role('button', name=name, exact=True).click()
                page.get_by_role('heading', name=heading, exact=True).wait_for()
                if name == '记忆与关系':
                    page.get_by_label('记忆内容', exact=True).fill('测试重要事件')
                    page.get_by_role('button', name='保存记忆', exact=True).click()
                    page.get_by_text('测试重要事件', exact=True).wait_for()
                else:
                    page.get_by_label('文档标题').fill('测试资料')
                    page.get_by_label('文档内容', exact=True).fill('这是一份可检索的测试文档。')
                    page.get_by_role('button', name='保存文档', exact=True).click()
                    page.get_by_text('测试资料 · owner', exact=True).wait_for()
            screens = ['插件与能力', '通信平台', '用量与资源', '初始化向导', '偏好与安全', '控制台与日志', '运行总览']
            for i, name in enumerate(screens):
                page.locator('nav').get_by_role('button', name=name, exact=True).click()
                page.get_by_role('heading', name=name, exact=True, level=1).wait_for()
                page.wait_for_timeout(150)
                assert not page.locator('#notice.error').inner_text() if page.locator('#notice.error').count() else True
                if name in ('运行总览', '偏好与安全', '插件与能力'):
                    page.evaluate('window.scrollTo(0,0)')
                    page.wait_for_timeout(100)
                    page.screenshot(path=str(out/f'ui-{i}.png'), full_page=True)
            for width in [900, 390]:
                page.set_viewport_size({'width':width,'height':900})
                page.wait_for_timeout(100)
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'horizontal overflow at {width}'
                page.screenshot(path=str(out/f'visual-width-{width}.png'), full_page=True)
            page.set_viewport_size({'width':1360,'height':950})
            # Skip link fragments must not replace local authentication on refresh.
            page.evaluate("location.hash='view'")
            page.reload()
            page.get_by_role('heading', name='与角色交谈 · 交付任务').wait_for()
            assert not errors, errors
            browser.close()
            print('UI: character create/save, memory add, knowledge import, all ten pages, token refresh passed')
    finally:
        httpd.shutdown(); httpd.server_close(); host.close(); host.store.db.close()
