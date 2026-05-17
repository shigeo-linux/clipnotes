import os
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from config import Config
from api_client import APIClient
from transcript_fetcher import extract_video_id, fetch_transcript, split_chunks
from summary_exporter import save_as_pdf
from markdown_exporter import summary_to_markdown, safe_filename
from ui.settings_dialog import SettingsDialog

STYLE_PATH = os.path.join(os.path.dirname(__file__), 'style.css')

SUMMARY_SYSTEM = """You are a professional content analyst. Your task is to watch — via its transcript — a YouTube video and produce a clear, concise one-page summary.

Your summary must contain:
1. A bold title line: the video's title or main topic
2. A 2-3 sentence overview of what the video covers
3. Between 5 and 10 bullet points covering the most important points, facts, arguments, or takeaways

Format your response exactly like this:

**[Video Title or Topic]**

[2-3 sentence overview]

• [Key point 1]
• [Key point 2]
• [Key point 3]
(continue for 5-10 points)

Be specific and informative. Use the actual names, facts, and details from the video. Avoid vague generalities."""

COMBINE_SYSTEM = """You are a professional content analyst. You have been given several partial summaries of sections of a long YouTube video. Combine them into a single cohesive one-page summary.

Your summary must contain:
1. A bold title line: the video's overall title or topic
2. A 2-3 sentence overview
3. Between 5 and 10 bullet points covering the most important points across the whole video

Format:

**[Video Title or Topic]**

[2-3 sentence overview]

• [Key point 1]
• [Key point 2]
(continue for 5-10 points)"""


def _load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(STYLE_PATH)
    except Exception:
        pass
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Clipnotes')
        self.set_default_size(780, 640)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name('clipnotes')
        _load_css()

        self.config = Config()
        self.api = APIClient(self.config)
        self._transcript = ''
        self._chunks = []
        self._chunk_summaries = []
        self._video_title = ''
        self._video_channel = ''
        self._busy = False

        self._build_ui()

    def _build_ui(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title('Clipnotes')
        self.set_titlebar(header)

        settings_btn = Gtk.Button()
        settings_btn.set_image(Gtk.Image.new_from_icon_name(
            'preferences-system-symbolic', Gtk.IconSize.BUTTON))
        settings_btn.set_tooltip_text('Settings')
        settings_btn.connect('clicked', self._on_settings)
        header.pack_end(settings_btn)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main)

        # API warning
        self._api_warning = Gtk.InfoBar()
        self._api_warning.set_message_type(Gtk.MessageType.WARNING)
        self._api_warning.get_content_area().pack_start(
            Gtk.Label(label='No API key set. Open Settings (⚙) to add your OpenRouter API key.'),
            True, True, 0
        )
        self._api_warning.add_button('Open Settings', 1)
        self._api_warning.connect('response', lambda bar, r: self._on_settings(None) if r == 1 else None)
        self._api_warning.set_no_show_all(True)
        main.pack_start(self._api_warning, False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_border_width(20)
        main.pack_start(content, True, True, 0)

        # URL input area
        url_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        url_area.get_style_context().add_class('url-area')

        url_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        url_label = Gtk.Label(label='YouTube URL:', xalign=0)
        url_row.pack_start(url_label, False, False, 0)

        entry_scroll = Gtk.ScrolledWindow()
        entry_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        entry_scroll.set_shadow_type(Gtk.ShadowType.NONE)
        entry_scroll.set_hexpand(True)
        entry_scroll.get_style_context().add_class('url-entry-scroll')

        self._url_entry = Gtk.Entry()
        self._url_entry.set_placeholder_text('https://www.youtube.com/watch?v=...')
        self._url_entry.get_style_context().add_class('url-entry')
        self._url_entry.connect('activate', self._on_fetch)
        entry_scroll.add(self._url_entry)
        url_row.pack_start(entry_scroll, True, True, 0)

        fetch_btn = Gtk.Button(label='Fetch')
        fetch_btn.get_style_context().add_class('action-btn')
        fetch_btn.connect('clicked', self._on_fetch)
        url_row.pack_start(fetch_btn, False, False, 0)
        url_area.pack_start(url_row, False, False, 0)

        # Video info
        video_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name('video-x-generic', Gtk.IconSize.LARGE_TOOLBAR)
        video_info.pack_start(icon, False, False, 0)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._video_title_label = Gtk.Label(label='Paste a YouTube URL above to get started', xalign=0)
        self._video_title_label.get_style_context().add_class('video-title')
        self._video_title_label.set_ellipsize(3)
        self._video_meta_label = Gtk.Label(label='', xalign=0)
        self._video_meta_label.get_style_context().add_class('video-meta')
        info_box.pack_start(self._video_title_label, False, False, 0)
        info_box.pack_start(self._video_meta_label, False, False, 0)
        video_info.pack_start(info_box, True, True, 0)
        url_area.pack_start(video_info, False, False, 0)
        content.pack_start(url_area, False, False, 0)

        # Generate row
        gen_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._gen_btn = Gtk.Button(label='Generate Summary')
        self._gen_btn.get_style_context().add_class('action-btn')
        self._gen_btn.connect('clicked', self._on_generate)
        self._gen_btn.set_sensitive(False)
        gen_row.pack_start(self._gen_btn, False, False, 0)

        self._spinner = Gtk.Spinner()
        gen_row.pack_start(self._spinner, False, False, 0)

        self._progress_label = Gtk.Label(label='', xalign=0)
        self._progress_label.get_style_context().add_class('video-meta')
        gen_row.pack_start(self._progress_label, False, False, 0)
        content.pack_start(gen_row, False, False, 0)

        # Summary area
        summary_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        summary_header.pack_start(Gtk.Label(label='Summary', xalign=0), True, True, 0)

        self._obsidian_btn = Gtk.Button(label='Save to Obsidian')
        self._obsidian_btn.get_style_context().add_class('action-btn')
        self._obsidian_btn.connect('clicked', self._on_save_obsidian)
        self._obsidian_btn.set_sensitive(False)
        summary_header.pack_end(self._obsidian_btn, False, False, 0)

        self._copy_btn = Gtk.Button(label='Copy')
        self._copy_btn.get_style_context().add_class('secondary-btn')
        self._copy_btn.connect('clicked', self._on_copy)
        self._copy_btn.set_sensitive(False)
        summary_header.pack_end(self._copy_btn, False, False, 0)

        self._save_pdf_btn = Gtk.Button(label='Save as PDF')
        self._save_pdf_btn.get_style_context().add_class('secondary-btn')
        self._save_pdf_btn.connect('clicked', self._on_save_pdf)
        self._save_pdf_btn.set_sensitive(False)
        summary_header.pack_end(self._save_pdf_btn, False, False, 0)

        self._save_btn = Gtk.Button(label='Save as TXT')
        self._save_btn.get_style_context().add_class('secondary-btn')
        self._save_btn.connect('clicked', self._on_save_txt)
        self._save_btn.set_sensitive(False)
        summary_header.pack_end(self._save_btn, False, False, 0)

        content.pack_start(summary_header, False, False, 0)

        summary_scroll = Gtk.ScrolledWindow()
        summary_scroll.set_vexpand(True)
        summary_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._summary_view = Gtk.TextView()
        self._summary_view.set_editable(False)
        self._summary_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._summary_view.set_left_margin(12)
        self._summary_view.set_right_margin(12)
        self._summary_view.set_top_margin(10)
        self._summary_view.set_bottom_margin(10)
        self._summary_view.get_style_context().add_class('summary-view')
        self._summary_buf = self._summary_view.get_buffer()
        summary_scroll.add(self._summary_view)
        content.pack_start(summary_scroll, True, True, 0)

        # Status bar
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._status_bar.get_style_context().add_class('status-bar')
        self._status_label = Gtk.Label(label='', xalign=0)
        self._status_bar.pack_start(self._status_label, True, True, 0)
        main.pack_start(self._status_bar, False, False, 0)

        self._check_api_key()

    def _on_fetch(self, widget):
        url = self._url_entry.get_text().strip()
        if not url or self._busy:
            return

        video_id = extract_video_id(url)
        if not video_id:
            self._show_error('Invalid URL', 'Please enter a valid YouTube URL.')
            return

        self._busy = True
        self._gen_btn.set_sensitive(False)
        self._spinner.start()
        self._set_progress('Fetching transcript…')
        self._summary_buf.set_text('')
        self._copy_btn.set_sensitive(False)
        self._save_btn.set_sensitive(False)
        self._save_pdf_btn.set_sensitive(False)
        self._obsidian_btn.set_sensitive(False)

        def run():
            try:
                text, lang, title, channel = fetch_transcript(video_id)
                GLib.idle_add(self._on_fetch_done, text, lang, title, channel)
            except Exception as e:
                GLib.idle_add(self._on_fetch_error, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_fetch_done(self, text, lang, title, channel):
        self._busy = False
        self._spinner.stop()
        self._transcript = text
        self._chunks = split_chunks(text)
        self._video_title = title
        self._video_channel = channel

        self._video_title_label.set_text(title or 'Untitled video')
        self._video_meta_label.set_text(
            f'{channel}  ·  {len(text):,} characters  ·  '
            f'Language: {lang}  ·  '
            f'{len(self._chunks)} chunk{"s" if len(self._chunks) > 1 else ""}'
        )
        self._gen_btn.set_sensitive(True)
        self._set_progress('')
        self._set_status('Transcript fetched — ready to summarise.')

    def _on_fetch_error(self, error_msg):
        self._busy = False
        self._spinner.stop()
        self._set_progress('')
        self._show_error('Could not fetch transcript', error_msg)

    def _on_generate(self, btn):
        if self._busy or not self._transcript:
            return
        self._busy = True
        self._gen_btn.set_sensitive(False)
        self._copy_btn.set_sensitive(False)
        self._save_btn.set_sensitive(False)
        self._save_pdf_btn.set_sensitive(False)
        self._obsidian_btn.set_sensitive(False)
        self._spinner.start()
        self._summary_buf.set_text('')
        self._chunk_summaries = []
        self._process_next_chunk()

    def _process_next_chunk(self):
        idx = len(self._chunk_summaries)
        total = len(self._chunks)
        if idx >= total:
            if total == 1:
                self._finalise(self._chunk_summaries[0])
            else:
                self._combine()
            return

        self._set_progress(
            f'Summarising part {idx + 1} of {total}…' if total > 1 else 'Generating summary…'
        )
        self.api.complete_async(
            messages=[{'role': 'user', 'content': f'Please summarise this video transcript section:\n\n{self._chunks[idx]}'}],
            system=SUMMARY_SYSTEM,
            on_done=self._on_chunk_done,
            on_error=self._on_error,
        )

    def _on_chunk_done(self, summary):
        self._chunk_summaries.append(summary)
        self._process_next_chunk()

    def _combine(self):
        self._set_progress('Combining summaries…')
        combined = '\n\n---\n\n'.join(
            f'Part {i + 1}:\n{s}' for i, s in enumerate(self._chunk_summaries)
        )
        self.api.complete_async(
            messages=[{'role': 'user', 'content': f'Combine these partial summaries:\n\n{combined}'}],
            system=COMBINE_SYSTEM,
            on_done=self._finalise,
            on_error=self._on_error,
        )

    def _finalise(self, summary):
        self._busy = False
        self._spinner.stop()
        self._gen_btn.set_sensitive(True)
        self._set_progress('')
        url = self._url_entry.get_text().strip()
        header_parts = []
        if self._video_channel:
            header_parts.append(f"Channel: {self._video_channel}")
        if url:
            header_parts.append(f"Source: {url}")
        header = '\n'.join(header_parts)
        full_summary = f"{header}\n\n{summary}" if header else summary
        self._summary_buf.set_text(full_summary)
        self._copy_btn.set_sensitive(True)
        self._save_btn.set_sensitive(True)
        self._save_pdf_btn.set_sensitive(True)
        self._obsidian_btn.set_sensitive(True)
        self._set_status('Summary complete.')

    def _on_error(self, error_msg):
        self._busy = False
        self._spinner.stop()
        self._gen_btn.set_sensitive(True)
        self._set_progress('')
        self._show_error('Could not generate summary', error_msg)

    def _on_copy(self, btn):
        buf = self._summary_buf
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)
        self._set_status('Summary copied to clipboard.')

    def _on_save_txt(self, btn):
        text = self._get_summary()
        if not text:
            return
        dialog = self._save_dialog('Save Summary as TXT', f'{self._safe_title()}_summary.txt')
        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self._set_status(f'Saved to {path}')
            except Exception as e:
                self._show_error('Could not save file', str(e))

    def _on_save_pdf(self, btn):
        text = self._get_summary()
        if not text:
            return
        dialog = self._save_dialog('Save Summary as PDF', f'{self._safe_title()}_summary.pdf',
                                   mime='application/pdf', pattern='*.pdf')
        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and path:
            try:
                source = self._video_title or self._url_entry.get_text().strip()
                save_as_pdf(text, path, source_filename=source)
                self._set_status(f'Saved PDF to {path}')
            except Exception as e:
                self._show_error('Could not save PDF', str(e))

    def _save_dialog(self, title, default_name, mime=None, pattern=None):
        dialog = Gtk.FileChooserDialog(
            title=title, transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(default_name)
        if mime or pattern:
            f = Gtk.FileFilter()
            if mime:
                f.add_mime_type(mime)
            if pattern:
                f.add_pattern(pattern)
            dialog.add_filter(f)
        return dialog

    def _get_summary(self):
        buf = self._summary_buf
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

    def _safe_title(self):
        title = self._video_title or 'clipnotes'
        return ''.join(c if c.isalnum() or c in ' _-' else '_' for c in title)[:40].strip()

    def _on_save_obsidian(self, btn):
        text = self._get_summary()
        if not text:
            return

        vault = self.config.get('obsidian_vault', '').strip()
        if not vault or not os.path.isdir(vault):
            self._show_error(
                'Obsidian vault not set',
                'Please open Settings and set the path to your Obsidian vault folder.'
            )
            return

        md = summary_to_markdown(
            text,
            video_title=self._video_title,
            channel=self._video_channel,
            url=self._url_entry.get_text().strip(),
        )
        filename = safe_filename(self._video_title)
        path = os.path.join(vault, filename)

        # Avoid overwriting — append a counter if needed
        if os.path.exists(path):
            base, ext = os.path.splitext(path)
            i = 2
            while os.path.exists(f'{base}_{i}{ext}'):
                i += 1
            path = f'{base}_{i}{ext}'

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(md)
            self._show_success(f'✓ Saved to Obsidian: {os.path.basename(path)}')
        except Exception as e:
            self._show_error('Could not save to Obsidian vault', str(e))

    def _on_settings(self, btn):
        dialog = SettingsDialog(self, self.config)
        resp = dialog.run()
        if resp == Gtk.ResponseType.OK:
            key, model, vault = dialog.get_values()
            self.config.api_key = key
            self.config.model = model
            self.config.set('obsidian_vault', vault)
            self.config.save()
            self.api = APIClient(self.config)
            self._check_api_key()
        dialog.destroy()

    def _check_api_key(self):
        if not self.config.api_key:
            self._api_warning.set_visible(True)
            self._api_warning.show_all()
        else:
            self._api_warning.set_visible(False)

    def _show_success(self, msg):
        self._status_label.set_markup(f'<span foreground="#2e7d32" weight="bold">{msg}</span>')
        GLib.timeout_add(4000, self._clear_success)

    def _clear_success(self):
        self._status_label.set_markup(f'<span>{self._status_label.get_text()}</span>')
        return False

    def _set_status(self, msg):
        self._status_label.set_text(msg)

    def _set_progress(self, msg):
        self._progress_label.set_text(msg)

    def _show_error(self, title, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(msg)
        dialog.run()
        dialog.destroy()
