using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using System.Threading;
using YoutubeExplode;
using YoutubeExplode.Common;
using YoutubeExplode.Videos;
using YoutubeExplode.Videos.Streams;

namespace YoutubeDownloader;

public sealed class MainForm : Form
{
    private readonly YoutubeClient _client = new();
    private readonly BindingList<StreamOption> _streamOptions = new();

    private readonly TextBox _urlTextBox;
    private readonly Button _fetchButton;
    private readonly Label _videoTitleLabel;
    private readonly Label _videoStatsLabel;
    private readonly CheckBox _audioOnlyCheckBox;
    private readonly ListBox _formatsListBox;
    private readonly Button _downloadButton;
    private readonly Button _cancelButton;
    private readonly Button _openFolderButton;
    private readonly Button _copyTitleButton;
    private readonly ProgressBar _progressBar;
    private readonly Label _statusLabel;
    private readonly ListView _historyListView;

    private CancellationTokenSource? _downloadCts;
    private Video? _currentVideo;
    private StreamManifest? _currentManifest;
    private string _downloadDirectory;

    public MainForm()
    {
        Text = "YouTube Downloader";
        MinimumSize = new System.Drawing.Size(900, 600);
        StartPosition = FormStartPosition.CenterScreen;

        var spacing = 8;
        var margin = 12;

        _urlTextBox = new TextBox
        {
            PlaceholderText = "YouTube-Link einfügen…",
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
            Left = margin,
            Top = margin,
            Width = ClientSize.Width - margin * 2 - 140
        };

        _fetchButton = new Button
        {
            Text = "Infos laden",
            Anchor = AnchorStyles.Top | AnchorStyles.Right,
            Left = _urlTextBox.Right + spacing,
            Top = margin,
            Width = 120
        };
        _fetchButton.Click += OnFetchClickedAsync;

        _audioOnlyCheckBox = new CheckBox
        {
            Text = "Nur Audio",
            Anchor = AnchorStyles.Top | AnchorStyles.Right,
            Left = _fetchButton.Right + spacing,
            Top = margin + 2,
            Checked = false,
            AutoSize = true
        };
        _audioOnlyCheckBox.CheckedChanged += (_, _) => RefreshStreamList();

        _videoTitleLabel = new Label
        {
            Text = "Kein Video geladen",
            Left = margin,
            Top = _urlTextBox.Bottom + spacing,
            AutoSize = true,
            Font = new Font(Font, FontStyle.Bold)
        };

        _videoStatsLabel = new Label
        {
            Text = string.Empty,
            Left = margin,
            Top = _videoTitleLabel.Bottom + spacing,
            AutoSize = true
        };

        _copyTitleButton = new Button
        {
            Text = "Titel kopieren",
            Left = margin,
            Top = _videoStatsLabel.Bottom + spacing,
            Width = 140,
            Enabled = false
        };
        _copyTitleButton.Click += (_, _) => Clipboard.SetText(_currentVideo?.Title ?? string.Empty);

        _formatsListBox = new ListBox
        {
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
            Left = margin,
            Top = _copyTitleButton.Bottom + spacing,
            Width = ClientSize.Width - margin * 2,
            Height = 160,
            DisplayMember = nameof(StreamOption.Description)
        };
        _formatsListBox.DataSource = _streamOptions;
        _formatsListBox.SelectedIndexChanged += (_, _) => UpdateDownloadState();

        _downloadButton = new Button
        {
            Text = "Download starten",
            Anchor = AnchorStyles.Top | AnchorStyles.Left,
            Left = margin,
            Top = _formatsListBox.Bottom + spacing,
            Width = 160,
            Enabled = false
        };
        _downloadButton.Click += OnDownloadClickedAsync;

        _cancelButton = new Button
        {
            Text = "Abbrechen",
            Anchor = AnchorStyles.Top | AnchorStyles.Left,
            Left = _downloadButton.Right + spacing,
            Top = _downloadButton.Top,
            Width = 120,
            Enabled = false
        };
        _cancelButton.Click += (_, _) => _downloadCts?.Cancel();

        _openFolderButton = new Button
        {
            Text = "Download-Ordner öffnen",
            Anchor = AnchorStyles.Top | AnchorStyles.Left,
            Left = _cancelButton.Right + spacing,
            Top = _downloadButton.Top,
            Width = 200
        };
        _openFolderButton.Click += (_, _) => OpenDownloadFolder();

        _progressBar = new ProgressBar
        {
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
            Left = margin,
            Top = _downloadButton.Bottom + spacing,
            Width = ClientSize.Width - margin * 2,
            Height = 26,
            Minimum = 0,
            Maximum = 100
        };

        _statusLabel = new Label
        {
            Left = margin,
            Top = _progressBar.Bottom + spacing,
            Width = ClientSize.Width - margin * 2,
            AutoEllipsis = true
        };

        _historyListView = new ListView
        {
            Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right,
            Left = margin,
            Top = _statusLabel.Bottom + spacing,
            Width = ClientSize.Width - margin * 2,
            Height = ClientSize.Height - (_statusLabel.Bottom + spacing + margin),
            View = View.Details,
            FullRowSelect = true,
            MultiSelect = false
        };
        _historyListView.Columns.Add("Titel", 360);
        _historyListView.Columns.Add("Format", 120);
        _historyListView.Columns.Add("Pfad", 260);
        _historyListView.Columns.Add("Zeit", 120);
        _historyListView.DoubleClick += OnHistoryDoubleClick;

        Controls.AddRange(new Control[]
        {
            _urlTextBox,
            _fetchButton,
            _audioOnlyCheckBox,
            _videoTitleLabel,
            _videoStatsLabel,
            _copyTitleButton,
            _formatsListBox,
            _downloadButton,
            _cancelButton,
            _openFolderButton,
            _progressBar,
            _statusLabel,
            _historyListView
        });

        Resize += (_, _) => ResizeControls();

        _downloadDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            "Downloads", "YoutubeDownloader");
        Directory.CreateDirectory(_downloadDirectory);
    }

    private void ResizeControls()
    {
        var margin = 12;
        var spacing = 8;

        _urlTextBox.Width = ClientSize.Width - margin * 2 - 140 - spacing * 2 - _audioOnlyCheckBox.Width;
        _fetchButton.Left = _urlTextBox.Right + spacing;
        _audioOnlyCheckBox.Left = _fetchButton.Right + spacing;

        _formatsListBox.Width = ClientSize.Width - margin * 2;
        _progressBar.Width = ClientSize.Width - margin * 2;
        _statusLabel.Width = ClientSize.Width - margin * 2;
        _historyListView.Width = ClientSize.Width - margin * 2;
        _historyListView.Height = ClientSize.Height - _historyListView.Top - margin;
    }

    private async void OnFetchClickedAsync(object? sender, EventArgs e)
    {
        var url = _urlTextBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(url))
        {
            MessageBox.Show("Bitte gib eine gültige YouTube-URL ein.", "Hinweis", MessageBoxButtons.OK,
                MessageBoxIcon.Information);
            return;
        }

        try
        {
            ToggleBusyState(true, "Video-Informationen werden geladen…");

            if (!VideoId.TryParse(url, out var videoId))
            {
                throw new InvalidOperationException("Die URL konnte keinem YouTube-Video zugeordnet werden.");
            }

            _currentVideo = await _client.Videos.GetAsync(videoId);
            _currentManifest = await _client.Videos.Streams.GetManifestAsync(videoId);

            _videoTitleLabel.Text = _currentVideo.Title;
            _videoStatsLabel.Text = BuildVideoDetails(_currentVideo);
            _copyTitleButton.Enabled = true;

            RefreshStreamList();
            _statusLabel.Text = "Video erfolgreich geladen.";
        }
        catch (Exception ex)
        {
            _statusLabel.Text = "Fehler beim Laden: " + ex.Message;
            MessageBox.Show(ex.Message, "Fehler", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            ToggleBusyState(false);
        }
    }

    private string BuildVideoDetails(Video video)
    {
        var builder = new StringBuilder();
        builder.AppendLine($"Autor: {video.Author.Title}");
        builder.AppendLine($"Dauer: {video.Duration?.ToString("hh\:mm\:ss") ?? "Unbekannt"}");
        builder.AppendLine($"Aufrufe: {video.Engagement.ViewCount:N0}");
        builder.Append($"Veröffentlicht: {video.UploadDate:dd.MM.yyyy}");
        return builder.ToString();
    }

    private void RefreshStreamList()
    {
        _streamOptions.Clear();

        if (_currentManifest is null)
        {
            return;
        }

        IEnumerable<IStreamInfo> streams = _audioOnlyCheckBox.Checked
            ? _currentManifest.GetAudioOnlyStreams().OrderByDescending(s => s.Bitrate)
            : _currentManifest.GetMuxedStreams().OrderByDescending(s => s.VideoQuality?.Resolution.Height ?? 0);

        foreach (var stream in streams)
        {
            _streamOptions.Add(new StreamOption(stream));
        }

        if (_streamOptions.Count == 0)
        {
            _statusLabel.Text = "Keine passenden Formate gefunden.";
        }

        UpdateDownloadState();
    }

    private async void OnDownloadClickedAsync(object? sender, EventArgs e)
    {
        if (_currentVideo is null || _formatsListBox.SelectedItem is not StreamOption option)
        {
            return;
        }

        var defaultFileName = BuildFileName(_currentVideo.Title, option.DefaultFileExtension);

        using var dialog = new SaveFileDialog
        {
            FileName = defaultFileName,
            InitialDirectory = _downloadDirectory,
            Filter = option.IsAudio ? "Audio|*.mp3;*.m4a;*.webm" : "Video|*.mp4;*.mkv;*.webm"
        };

        if (dialog.ShowDialog(this) != DialogResult.OK)
        {
            return;
        }

        _downloadDirectory = Path.GetDirectoryName(dialog.FileName) ?? _downloadDirectory;

        _downloadCts = new CancellationTokenSource();
        ToggleBusyState(true, "Download läuft…");
        _downloadButton.Enabled = false;
        _cancelButton.Enabled = true;
        _progressBar.Value = 0;

        try
        {
            var progress = new Progress<double>(value =>
            {
                var percentage = (int)Math.Round(value * 100);
                _progressBar.Value = Math.Clamp(percentage, 0, 100);
                _statusLabel.Text = $"Downloadfortschritt: {percentage}%";
            });

            await _client.Videos.Streams.DownloadAsync(option.StreamInfo, dialog.FileName, progress,
                _downloadCts.Token);

            _statusLabel.Text = "Download abgeschlossen.";
            _progressBar.Value = 100;
            AddHistoryEntry(_currentVideo, option, dialog.FileName);
        }
        catch (OperationCanceledException)
        {
            _statusLabel.Text = "Download abgebrochen.";
        }
        catch (Exception ex)
        {
            _statusLabel.Text = "Fehler beim Download: " + ex.Message;
            MessageBox.Show(ex.Message, "Fehler", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            _downloadCts?.Dispose();
            _downloadCts = null;
            _cancelButton.Enabled = false;
            ToggleBusyState(false);
            UpdateDownloadState();
        }
    }

    private void AddHistoryEntry(Video video, StreamOption option, string filePath)
    {
        var item = new ListViewItem(new[]
        {
            video.Title,
            option.Description,
            filePath,
            DateTime.Now.ToString("dd.MM.yyyy HH:mm")
        })
        {
            Tag = filePath
        };

        _historyListView.Items.Insert(0, item);
        _historyListView.SelectedItems.Clear();
        item.Selected = true;
    }

    private void UpdateDownloadState()
    {
        _downloadButton.Enabled = _currentVideo is not null && _formatsListBox.SelectedItem is StreamOption &&
                                   _downloadCts is null;
    }

    private void ToggleBusyState(bool busy, string? status = null)
    {
        UseWaitCursor = busy;
        _fetchButton.Enabled = !busy;
        _urlTextBox.Enabled = !busy;
        _audioOnlyCheckBox.Enabled = !busy;

        if (!busy)
        {
            Cursor = Cursors.Default;
        }

        if (status is not null)
        {
            _statusLabel.Text = status;
        }
    }

    private void OpenDownloadFolder()
    {
        try
        {
            Directory.CreateDirectory(_downloadDirectory);

            if (OperatingSystem.IsWindows())
            {
                Process.Start(new ProcessStartInfo("explorer.exe", _downloadDirectory) { UseShellExecute = true });
            }
            else if (OperatingSystem.IsLinux())
            {
                Process.Start("xdg-open", _downloadDirectory);
            }
            else if (OperatingSystem.IsMacOS())
            {
                Process.Start("open", _downloadDirectory);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show("Ordner konnte nicht geöffnet werden: " + ex.Message, "Fehler",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void OnHistoryDoubleClick(object? sender, EventArgs e)
    {
        if (_historyListView.SelectedItems.Count == 0)
        {
            return;
        }

        var path = _historyListView.SelectedItems[0].Tag as string;
        if (string.IsNullOrWhiteSpace(path))
        {
            return;
        }

        if (!File.Exists(path))
        {
            MessageBox.Show("Die Datei konnte nicht gefunden werden.", "Hinweis", MessageBoxButtons.OK,
                MessageBoxIcon.Information);
            return;
        }

        try
        {
            Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show("Datei konnte nicht geöffnet werden: " + ex.Message, "Fehler", MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }

    private static string BuildFileName(string title, string extension)
    {
        var invalidChars = Path.GetInvalidFileNameChars();
        var sanitized = new string(title.Select(ch => invalidChars.Contains(ch) ? '_' : ch).ToArray());
        return sanitized + extension;
    }

    private sealed record StreamOption(IStreamInfo StreamInfo)
    {
        public bool IsAudio => StreamInfo is IAudioStreamInfo;

        public string DefaultFileExtension
        {
            get
            {
                var container = StreamInfo.Container.Name.ToLowerInvariant();
                return container switch
                {
                    "mp4" when IsAudio => ".m4a",
                    "mp4" => ".mp4",
                    "webm" => ".webm",
                    "m4a" => ".m4a",
                    "ogg" when IsAudio => ".ogg",
                    _ => IsAudio ? ".mp3" : ".mp4"
                };
            }
        }

        public string Description
        {
            get
            {
                return StreamInfo switch
                {
                    MuxedStreamInfo muxed =>
                        $"Video {muxed.VideoQuality.Label} • {muxed.Container} • {muxed.Size.MegaBytes:F0} MB",
                    AudioOnlyStreamInfo audio =>
                        $"Audio {audio.Bitrate.KiloBitsPerSecond:F0} kbps • {audio.Container} • {audio.Size.MegaBytes:F0} MB",
                    _ => StreamInfo.ToString() ?? "Unbekannt"
                };
            }
        }
    }
}
