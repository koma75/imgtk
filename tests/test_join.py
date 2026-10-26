"""join subcommand: PDF assembly from a directory/explicit files, config, ext filter,
ordering, dpi scaling, catalog viewer keys, /PageMode, and /OpenAction zoom.
"""
from __future__ import annotations
from .infra import run_cli, scenario, FIXTURES
from .fixtures import JOIN_SIZES, TOC_FIXTURE
from .pdfinspect import expect_pdf, expect_pdf_toc, pdf_pages, pdf_page_layout, pdf_direction, pdf_page_mode, pdf_open_action
JOIN_ORDER_DEFAULT = ['01_first.jpg', '02_mid.png', '10_last.jpg']
JOIN_ORDER_GIF = ['01_first.jpg', '02_mid.png', '03_skip.gif', '10_last.jpg']
JOIN_ORDER_CUSTOM = ['01_first.jpg', '03_skip.gif', '10_last.jpg']

def test_join_generates_default_config():
    root = scenario('join_default', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'out.pdf'], cwd=root)
    cfg = root / 'imgtk-join.yml'
    assert cfg.exists()
    assert cfg.read_text() == 'out: output.pdf\ntoc: toc.yml\ndpi: 96\next:\n  - jpg\n  - jpeg\n  - png\npage_layout: TwoPageRight\ndirection: R2L\n', 'generated default config does not match the defaults documented in README.md'
    expect_pdf(root, 'out.pdf', JOIN_ORDER_DEFAULT, 96, 'default config')

def test_join_filters_directory_by_extension():
    root = scenario('join_ext', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'filtered.pdf'], cwd=root)
    data = expect_pdf(root, 'filtered.pdf', JOIN_ORDER_DEFAULT, 96, 'config ext filter')
    pages = pdf_pages(data)
    assert len(pages) == 3, 'jpg/jpeg/png ext filter should pick 3 of the 5 directory entries'
    assert sorted((s for _w, _h, sizes in pages for s in sizes)) == [(60, 100), (90, 130), (120, 180)], 'ext filter embedded the wrong images'

def test_join_ext_option_adds_extension():
    root = scenario('join_extopt', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'withgif.pdf', '-e', 'gif'], cwd=root)
    expect_pdf(root, 'withgif.pdf', JOIN_ORDER_GIF, 96, 'cli -e gif')

def test_join_directory_entries_sort_numerically():
    root = scenario('join_order', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'ordered.pdf'], cwd=root)
    data = expect_pdf(root, 'ordered.pdf', JOIN_ORDER_DEFAULT, 96, 'numeric ordering')
    assert pdf_pages(data)[1][2] != [JOIN_SIZES['10_last.jpg']], '02_mid.png must sort before 10_last.jpg numerically'

def test_join_explicit_files_keep_given_order():
    root = scenario('join_explicit', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir/10_last.jpg', 'join/srcdir/01_first.jpg', '-o', 'explicit.pdf'], cwd=root)
    expect_pdf(root, 'explicit.pdf', ['10_last.jpg', '01_first.jpg'], 96, 'explicit file order')

def test_join_pdf_outline_from_toc():
    root = scenario('join_toc', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'withtoc.pdf', '-t', 'join/toc.yml'], cwd=root)
    data = expect_pdf(root, 'withtoc.pdf', JOIN_ORDER_DEFAULT, 96, 'toc outline')
    outlines = expect_pdf_toc(data, TOC_FIXTURE, 'toc outline')
    assert len(outlines) == len(TOC_FIXTURE), 'PDF outline has {0} entries, toc fixture declares {1}'.format(len(outlines), len(TOC_FIXTURE))

def test_join_config_file_supplies_defaults():
    root = scenario('join_custom', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-c', 'join/custom.yml'], cwd=root)
    assert (root / 'custom-out.pdf').exists()
    assert not (root / 'output.pdf').exists()
    expect_pdf(root, 'custom-out.pdf', JOIN_ORDER_CUSTOM, 48, 'custom config out/dpi/ext keys')

def test_join_dpi_option_scales_pages():
    root = scenario('join_dpi', src=FIXTURES / 'join')
    run_cli(['join', 'join/srcdir', '-o', 'dpi96.pdf'], cwd=root)
    run_cli(['join', 'join/srcdir', '-o', 'dpi48.pdf', '-d', '48'], cwd=root)
    base = pdf_pages(expect_pdf(root, 'dpi96.pdf', JOIN_ORDER_DEFAULT, 96, 'default dpi'))
    half = pdf_pages(expect_pdf(root, 'dpi48.pdf', JOIN_ORDER_DEFAULT, 48, '-d 48'))
    assert [p[2] for p in base] == [p[2] for p in half], '-d 48 changed the embedded image sizes'
    for i in range(len(base)):
        assert abs(half[i][0] - base[i][0] * 2) <= 0.1, 'page {0} width not doubled by -d 48: {1} vs {2}'.format(i + 1, half[i][0], base[i][0])
        assert abs(half[i][1] - base[i][1] * 2) <= 0.1, 'page {0} height not doubled by -d 48: {1} vs {2}'.format(i + 1, half[i][1], base[i][1])

def test_join_bad_extension_entry_does_not_crash():
    root = scenario('join_txt', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'txt.pdf', '-e', 'txt'], cwd=root)
    assert rc == 0, 'join should survive unreadable entries in the directory'
    data = expect_pdf(root, 'txt.pdf', JOIN_ORDER_DEFAULT, 96, 'txt entry skipped')
    assert len(pdf_pages(data)) == 3, 'notes.txt must never become a PDF page'

def test_join_catalog_viewer_defaults_documented():
    root = scenario('join_catalog', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'spread.pdf'], cwd=root)
    data = expect_pdf(root, 'spread.pdf', JOIN_ORDER_DEFAULT, 96, 'catalog defaults')
    assert pdf_page_layout(data) == 'TwoPageRight', 'default /PageLayout is {0}, README documents TwoPageRight'.format(pdf_page_layout(data))
    assert pdf_direction(data) == 'R2L', 'default /Direction is {0}, README documents R2L'.format(pdf_direction(data))

def test_join_page_layout_option():
    root = scenario('join_layout', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'single.pdf', '--page-layout', 'SinglePage'], cwd=root)
    data = expect_pdf(root, 'single.pdf', JOIN_ORDER_DEFAULT, 96, '--page-layout SinglePage')
    assert pdf_page_layout(data) == 'SinglePage', '--page-layout SinglePage produced /PageLayout {0}'.format(pdf_page_layout(data))
    run_cli(['join', 'join/srcdir', '-o', 'twocol.pdf', '-P', 'TwoColumnRight'], cwd=root)
    data = expect_pdf(root, 'twocol.pdf', JOIN_ORDER_DEFAULT, 96, '-P TwoColumnRight')
    assert pdf_page_layout(data) == 'TwoColumnRight', '-P TwoColumnRight produced /PageLayout {0}'.format(pdf_page_layout(data))
    run_cli(['join', 'join/srcdir', '-o', 'l2r.pdf', '-D', 'L2R'], cwd=root)
    data = expect_pdf(root, 'l2r.pdf', JOIN_ORDER_DEFAULT, 96, '-D L2R')
    assert pdf_direction(data) == 'L2R', '-D L2R produced /Direction {0}'.format(pdf_direction(data))

def test_join_catalog_keys_from_config():
    root = scenario('join_catalogcfg', src=FIXTURES / 'join')
    (root / 'catalog.yml').write_text('out: cfgcatalog.pdf\npage_layout: twocolumnleft\ndirection: l2r\next:\n  - jpg\n  - png\n')
    rc, out, err = run_cli(['join', 'join/srcdir', '-c', 'catalog.yml'], cwd=root)
    data = expect_pdf(root, 'cfgcatalog.pdf', JOIN_ORDER_DEFAULT, 96, 'config page_layout/direction keys')
    assert pdf_page_layout(data) == 'TwoColumnLeft', "config 'page_layout: twocolumnleft' produced /PageLayout {0}".format(pdf_page_layout(data))
    assert pdf_direction(data) == 'L2R', "config 'direction: l2r' produced /Direction {0}".format(pdf_direction(data))
    rc, out, err = run_cli(['join', 'join/srcdir', '-c', 'catalog.yml', '-D', 'R2L', '-o', 'cfgcli.pdf'], cwd=root)
    data = expect_pdf(root, 'cfgcli.pdf', JOIN_ORDER_DEFAULT, 96, 'cli -D overrides config direction')
    assert pdf_direction(data) == 'R2L', 'cli --direction did not override the config value: {0}'.format(pdf_direction(data))
    assert pdf_page_layout(data) == 'TwoColumnLeft', 'config page_layout was dropped when only --direction was given'

def test_join_catalog_entries_can_be_disabled():
    root = scenario('join_nocat', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'plain.pdf', '-P', 'none', '-D', 'none'], cwd=root)
    data = expect_pdf(root, 'plain.pdf', JOIN_ORDER_DEFAULT, 96, '-P none -D none')
    assert pdf_page_layout(data) is None, '--page-layout none must remove /PageLayout, found {0}'.format(pdf_page_layout(data))
    assert pdf_direction(data) is None, '--direction none must remove /Direction, found {0}'.format(pdf_direction(data))

def test_join_none_differs_from_omitted_config_key():
    root = scenario('join_nonecfg', src=FIXTURES / 'join')
    (root / 'nonecfg.yml').write_text('out: nonecfg.pdf\next:\n  - jpg\n  - png\npage_layout: none\n')
    rc, out, err = run_cli(['join', 'join/srcdir', '-c', 'nonecfg.yml'], cwd=root)
    data = expect_pdf(root, 'nonecfg.pdf', JOIN_ORDER_DEFAULT, 96, 'config page_layout: none')
    assert pdf_page_layout(data) is None, "'page_layout: none' left /PageLayout {0} in the catalog".format(pdf_page_layout(data))
    assert pdf_direction(data) == 'R2L', 'omitted direction key must fall back to the R2L default: {0}'.format(pdf_direction(data))

def test_join_failed_write_leaves_no_partial_file():
    root = scenario('join_nowrite', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'nodir/out.pdf'], cwd=root, expect_rc=1)
    assert 'could not write' in out + err, 'write failure not reported'
    assert not (root / 'out.pdf').exists()
    leftovers = [str(p.name) for p in root.iterdir() if p.name.endswith('.tmp')]
    assert leftovers == [], 'temporary staging files left behind: {0}'.format(leftovers)

def test_join_rejects_invalid_catalog_setting():
    root = scenario('join_badcatalog', src=FIXTURES / 'join')
    (root / 'badcatalog.yml').write_text('page_layout: Booklet\n')
    rc, out, err = run_cli(['join', 'join/srcdir', '-c', 'badcatalog.yml'], cwd=root, expect_rc=1)
    assert 'invalid page_layout' in out + err, 'invalid config page_layout value not reported'
    rc, out, err = run_cli(['join', 'join/srcdir', '-D', 'TTB'], cwd=root, expect_rc=None)
    assert rc != 0, 'invalid --direction value was accepted'
    assert 'not one of' in out + err, 'invalid --direction value not rejected by the cli'
    rc, out, err = run_cli(['join', 'join/srcdir', '-z', 'banana'], cwd=root, expect_rc=1)
    assert 'invalid zoom' in out + err, 'invalid --zoom value not reported by the resolver'

def test_join_page_mode_option():
    root = scenario('join_page_mode', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'pm_out.pdf', '-m', 'UseOutlines'], cwd=root)
    data = expect_pdf(root, 'pm_out.pdf', JOIN_ORDER_DEFAULT, 96, '-m UseOutlines')
    assert pdf_page_mode(data) == 'UseOutlines', '-m UseOutlines produced /PageMode {0}'.format(pdf_page_mode(data))
    run_cli(['join', 'join/srcdir', '-o', 'pm_none.pdf', '-m', 'none'], cwd=root)
    data = expect_pdf(root, 'pm_none.pdf', JOIN_ORDER_DEFAULT, 96, '-m none')
    assert pdf_page_mode(data) is None, '-m none must remove /PageMode, found {0}'.format(pdf_page_mode(data))

def test_join_page_mode_auto_default_from_toc():
    root = scenario('join_pmauto', src=FIXTURES / 'join')
    rc, out, err = run_cli(['join', 'join/srcdir', '-o', 'tocauto.pdf', '-t', 'join/toc.yml'], cwd=root)
    data = expect_pdf(root, 'tocauto.pdf', JOIN_ORDER_DEFAULT, 96, 'outline auto default')
    outlines = expect_pdf_toc(data, TOC_FIXTURE, 'outline auto default')
    assert pdf_page_mode(data) == 'UseOutlines', 'when the run wrote an outline, page_mode auto default must produce /PageMode UseOutlines, found {0}'.format(pdf_page_mode(data))
    run_cli(['join', 'join/srcdir', '-o', 'noauto.pdf'], cwd=root)
    data = expect_pdf(root, 'noauto.pdf', JOIN_ORDER_DEFAULT, 96, 'no outline')
    assert pdf_page_mode(data) is None, 'no outline written must leave /PageMode absent, found {0}'.format(pdf_page_mode(data))

def test_join_zoom_option():
    root = scenario('join_zoom', src=FIXTURES / 'join')
    run_cli(['join', 'join/srcdir', '-o', 'z150.pdf', '-z', '150%'], cwd=root)
    data = expect_pdf(root, 'z150.pdf', JOIN_ORDER_DEFAULT, 96, '-z 150%')
    assert pdf_open_action(data) == 'page=1,xyz,zoom=1.5', '-z 150% wrote an /OpenAction {0}'.format(pdf_open_action(data))
    run_cli(['join', 'join/srcdir', '-o', 'zfit.pdf', '-z', 'fit_page'], cwd=root)
    data = expect_pdf(root, 'zfit.pdf', JOIN_ORDER_DEFAULT, 96, '-z fit_page')
    assert pdf_open_action(data) == 'page=1,fit=Fit', '-z fit_page wrote /OpenAction {0}'.format(pdf_open_action(data))
    run_cli(['join', 'join/srcdir', '-o', 'zact.pdf', '-z', 'actual'], cwd=root)
    data = expect_pdf(root, 'zact.pdf', JOIN_ORDER_DEFAULT, 96, '-z actual')
    assert pdf_open_action(data) == 'page=1,xyz,zoom=1', '-z actual wrote /OpenAction {0}'.format(pdf_open_action(data))

def test_join_default_omits_open_action():
    root = scenario('join_noaction', src=FIXTURES / 'join')
    run_cli(['join', 'join/srcdir', '-o', 'noaction.pdf'], cwd=root)
    data = expect_pdf(root, 'noaction.pdf', JOIN_ORDER_DEFAULT, 96, 'no /OpenAction')
    assert pdf_open_action(data) == 'none', "default must not keep the generator's /OpenAction, found {0}".format(pdf_open_action(data))
    run_cli(['join', 'join/srcdir', '-o', 'znone.pdf', '-z', 'none'], cwd=root)
    data = expect_pdf(root, 'znone.pdf', JOIN_ORDER_DEFAULT, 96, '-z none')
    assert pdf_open_action(data) == 'none', '-z none must remove /OpenAction, found {0}'.format(pdf_open_action(data))

def test_join_zoom_and_page_mode_from_config():
    root = scenario('join_zoomcfg', src=FIXTURES / 'join')
    (root / 'zm.yml').write_text('out: zmcfg.pdf\npage_mode: fullscreen\nzoom: fit_width\next:\n  - jpg\n  - png\n')
    rc, out, err = run_cli(['join', 'join/srcdir', '-c', 'zm.yml'], cwd=root)
    data = expect_pdf(root, 'zmcfg.pdf', JOIN_ORDER_DEFAULT, 96, 'config page_mode/zoom')
    assert pdf_page_mode(data) == 'FullScreen', "config 'page_mode: fullscreen' produced /PageMode {0}".format(pdf_page_mode(data))
    assert pdf_open_action(data) == 'page=1,fit=FitH', "config 'zoom: fit_width' produced /OpenAction {0}".format(pdf_open_action(data))
    rc, out, err = run_cli(['join', 'join/srcdir', '-c', 'zm.yml', '-m', 'UseNone', '-z', 'fit_height', '-o', 'zmcli.pdf'], cwd=root)
    data = expect_pdf(root, 'zmcli.pdf', JOIN_ORDER_DEFAULT, 96, 'cli overrides config zoom/page_mode')
    assert pdf_page_mode(data) == 'UseNone', 'cli --page-mode did not override the config value: {0}'.format(pdf_page_mode(data))
    assert pdf_open_action(data) == 'page=1,fit=FitV', 'cli --zoom did not override the config value: {0}'.format(pdf_open_action(data))
