using System;
using System.Windows.Forms;

namespace YoutubeDownloader;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}
