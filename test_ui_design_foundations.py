"""Six resolved appearances, four cards and fixed modes without preference loss."""
def main():
    import copy,json
    from pathlib import Path
    from gui import MainWindow
    from modern_settings import SettingsDialog
    from tools.window_capture import capture_client
    from utils import CONFIG_FILE
    from ui_tokens import DESIGNS,FIXED_MODES
    from theme_catalog import theme_key
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    try:
        app.settings.update(design='atlas',color_mode='system')
        saved=copy.deepcopy(app.settings);disk=CONFIG_FILE.read_bytes()
        for design,fixed in FIXED_MODES.items():
            dialog=SettingsDialog(app);app.update();editor=dialog.content
            assert set(editor.design_cards)==set(DESIGNS)
            editor.design_cards[design].invoke();app.update()
            editor=app._settings_editor;app.update()
            assert app.theme_family==design and app.ui_theme==fixed
            assert editor.display_color_mode.get()==fixed
            assert editor.vars['color_mode'].get()=='system'
            assert all(b.disabled for b in editor.color_selector.buttons.values())
            editor.color_selector.select('dark' if fixed=='light' else 'light')
            assert editor.vars['color_mode'].get()=='system'
            assert app.settings==saved and CONFIG_FILE.read_bytes()==disk
            assert editor.collect()['design']==design and editor.collect()['color_mode']=='system'
            assert editor.design_cards[design].radius==(22 if design=='pano' else 0)
            cards=editor.design_cards
            dialog=editor.winfo_toplevel();dialog.geometry('960x760+20+20');app.update()
            if design=='yorunge':
                ordered=[cards[key] for key in DESIGNS]
                assert len({card.winfo_rooty() for card in ordered})==1,'Wide Yörünge cards must share one row'
                widths=[card.winfo_width() for card in ordered]
                assert max(widths)-min(widths)<=1,('Unequal Yörünge design cards',widths)
                for left,right in zip(ordered,ordered[1:]):assert left.winfo_rootx()+left.winfo_width()<right.winfo_rootx()
                dialog.geometry('760x700+20+20');app.update()
            assert cards['atlas'].winfo_rootx()==cards['pano'].winfo_rootx()
            assert cards['odak'].winfo_rootx()==cards['yorunge'].winfo_rootx()
            assert cards['atlas'].winfo_rootx()+cards['atlas'].winfo_width()<cards['odak'].winfo_rootx()
            assert cards['atlas'].winfo_rooty()+cards['atlas'].winfo_height()<cards['pano'].winfo_rooty()
            dialog.geometry('960x760+20+20');app.update()
            capture_client(dialog).save(Path('build')/f'phase1-design-{design}-settings.png')
            editor.design_cards['atlas'].invoke();app.update();editor=app._settings_editor
            assert not any(b.disabled for b in editor.color_selector.buttons.values())
            assert editor.display_color_mode.get()==editor.vars['color_mode'].get()=='system'
            editor.cancel();app.update()
            assert app.settings==saved and CONFIG_FILE.read_bytes()==disk
            assert app.theme_family=='atlas' and theme_key(saved)=='atlas_'+app.ui_theme
        dialog=SettingsDialog(app);app.update();dialog.content.design_cards['yorunge'].invoke();app.update()
        editor=app._settings_editor;assert editor.save();app.update()
        persisted=json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        assert persisted['design']=='yorunge' and persisted['color_mode']=='system'
        assert app.settings['design']=='yorunge' and app.settings['color_mode']=='system'
        dialog=SettingsDialog(app);app.update();dialog.content.design_cards['atlas'].invoke();app.update()
        editor=app._settings_editor
        assert editor.display_color_mode.get()=='system' and not any(b.disabled for b in editor.color_selector.buttons.values())
        editor.cancel();app.update();assert app.theme_family=='yorunge' and app.ui_theme=='dark'
        assert not errors,errors
        print('Four aligned design cards, fixed-mode selector, preserved System preference, live preview/cancel, unchanged profile bytes and real Save/reopen: OK')
    finally:app.engine.stop_engine();app.destroy()

if __name__=='__main__':main()
