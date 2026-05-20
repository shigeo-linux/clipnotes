import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

MODELS = [
    'openrouter/auto',
    'anthropic/claude-3.5-sonnet',
    'anthropic/claude-3-opus',
    'openai/gpt-4o',
    'openai/gpt-4o-mini',
    'google/gemini-pro-1.5',
]


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, config):
        super().__init__(title='Settings', transient_for=parent, modal=True)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(480, 240)

        box = self.get_content_area()
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)
        grid.set_border_width(20)
        box.pack_start(grid, True, True, 0)

        grid.attach(Gtk.Label(label='OpenRouter API Key:', xalign=1), 0, 0, 1, 1)
        self._key_entry = Gtk.Entry()
        self._key_entry.set_hexpand(True)
        self._key_entry.set_visibility(False)
        self._key_entry.set_text(config.api_key)
        self._key_entry.set_placeholder_text('sk-or-...')
        grid.attach(self._key_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label='Model:', xalign=1), 0, 1, 1, 1)
        self._model_combo = Gtk.ComboBoxText()
        for m in MODELS:
            self._model_combo.append(m, m)
        if config.model in MODELS:
            self._model_combo.set_active_id(config.model)
        else:
            self._model_combo.set_active(0)
        grid.attach(self._model_combo, 1, 1, 1, 1)

        link = Gtk.Label()
        link.set_markup('<a href="https://openrouter.ai/keys">Get a free API key at openrouter.ai</a>')
        link.set_xalign(0)
        grid.attach(link, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label='Obsidian Vault:', xalign=1), 0, 3, 1, 1)
        vault_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._vault_entry = Gtk.Entry()
        self._vault_entry.set_hexpand(True)
        self._vault_entry.set_text(config.get('obsidian_vault', ''))
        self._vault_entry.set_placeholder_text('Path to your Obsidian vault folder')
        vault_box.pack_start(self._vault_entry, True, True, 0)

        browse_btn = Gtk.Button(label='Browse…')
        browse_btn.connect('clicked', self._on_browse_vault)
        vault_box.pack_start(browse_btn, False, False, 0)
        grid.attach(vault_box, 1, 3, 1, 1)

        self.show_all()

    def _on_browse_vault(self, btn):
        dialog = Gtk.FileChooserDialog(
            title='Select Obsidian Vault Folder',
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        current = self._vault_entry.get_text()
        if current and os.path.isdir(current):
            dialog.set_current_folder(current)
        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and path:
            self._vault_entry.set_text(path)

    def get_values(self):
        return (self._key_entry.get_text().strip(),
                self._model_combo.get_active_id(),
                self._vault_entry.get_text().strip())
