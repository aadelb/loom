import * as vscode from 'vscode';
import { LoomClient } from './client';

let loomClient: LoomClient;
let statusBarItem: vscode.StatusBarItem;
let outputChannel: vscode.OutputChannel;

export async function activate(context: vscode.ExtensionContext) {
  // Initialize output channel and status bar
  outputChannel = vscode.window.createOutputChannel('Loom');
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.command = 'loom.health';
  statusBarItem.text = '$(loading~spin) Loom: Checking...';
  statusBarItem.show();

  // Initialize Loom client
  const config = vscode.workspace.getConfiguration('loom');
  const serverUrl = config.get<string>('serverUrl') || 'http://localhost:8787';
  const apiKey = config.get<string>('apiKey') || process.env.LOOM_API_KEY || '';

  loomClient = new LoomClient(serverUrl, apiKey);

  // Register command: loom.search
  const searchCommand = vscode.commands.registerCommand(
    'loom.search',
    async () => {
      const query = await vscode.window.showInputBox({
        prompt: 'Enter search query',
        placeHolder: 'e.g., "climate change policy"',
      });

      if (!query) {
        return;
      }

      try {
        outputChannel.appendLine(`[Loom Search] Query: ${query}`);
        outputChannel.show();

        const results = await loomClient.search(query);
        outputChannel.appendLine(
          `\n[Results] Found ${results.length} items:\n`
        );
        results.forEach((result, index) => {
          outputChannel.appendLine(`\n${index + 1}. ${result.title || 'Untitled'}`);
          if (result.url) {
            outputChannel.appendLine(`   URL: ${result.url}`);
          }
          if (result.snippet) {
            outputChannel.appendLine(`   ${result.snippet}`);
          }
        });
      } catch (error) {
        outputChannel.appendLine(
          `[Error] ${error instanceof Error ? error.message : String(error)}`
        );
        vscode.window.showErrorMessage(
          `Loom search failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    }
  );

  // Register command: loom.deep
  const deepCommand = vscode.commands.registerCommand(
    'loom.deep',
    async () => {
      const query = await vscode.window.showInputBox({
        prompt: 'Enter deep research query',
        placeHolder: 'e.g., "quantum computing breakthroughs 2025"',
      });

      if (!query) {
        return;
      }

      try {
        outputChannel.appendLine(`[Loom Deep Research] Query: ${query}`);
        outputChannel.show();

        // Create webview panel for deep research results
        const panel = vscode.window.createWebviewPanel(
          'loomDeepResearch',
          `Deep Research: ${query}`,
          vscode.ViewColumn.Two,
          {
            enableScripts: true,
          }
        );

        // Set loading state
        panel.webview.html = getLoadingHtml();

        // Fetch deep research results
        const results = await loomClient.deepResearch(query);

        // Update webview with results
        panel.webview.html = getDeepResearchHtml(results);
      } catch (error) {
        outputChannel.appendLine(
          `[Error] ${error instanceof Error ? error.message : String(error)}`
        );
        vscode.window.showErrorMessage(
          `Loom deep research failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    }
  );

  // Register command: loom.reframe
  const reframeCommand = vscode.commands.registerCommand(
    'loom.reframe',
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage('No active text editor');
        return;
      }

      const selection = editor.selection;
      const selectedText = editor.document.getText(selection);

      if (!selectedText) {
        vscode.window.showErrorMessage('Please select text to reframe');
        return;
      }

      try {
        outputChannel.appendLine(`[Loom Reframe] Original: ${selectedText}`);

        const reframedText = await loomClient.reframe(selectedText);

        // Replace selected text with reframed version
        await editor.edit((editBuilder) => {
          editBuilder.replace(selection, reframedText);
        });

        outputChannel.appendLine(`[Loom Reframe] Reframed: ${reframedText}`);
        vscode.window.showInformationMessage('Text reframed successfully');
      } catch (error) {
        outputChannel.appendLine(
          `[Error] ${error instanceof Error ? error.message : String(error)}`
        );
        vscode.window.showErrorMessage(
          `Loom reframe failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    }
  );

  // Register command: loom.health
  const healthCommand = vscode.commands.registerCommand(
    'loom.health',
    async () => {
      try {
        outputChannel.appendLine('[Loom Health Check] Checking server...');
        const health = await loomClient.checkHealth();

        statusBarItem.text = '$(check) Loom: Connected';
        statusBarItem.tooltip = `Loom Server Healthy\nURL: ${loomClient.serverUrl}`;

        outputChannel.appendLine(`[Health] Server is healthy`);
        outputChannel.appendLine(`Status: ${JSON.stringify(health, null, 2)}`);
        vscode.window.showInformationMessage('Loom server is healthy');
      } catch (error) {
        statusBarItem.text = '$(error) Loom: Disconnected';
        statusBarItem.tooltip = `Loom Server Unreachable\nError: ${error instanceof Error ? error.message : 'Unknown error'}`;

        outputChannel.appendLine(
          `[Error] ${error instanceof Error ? error.message : String(error)}`
        );
        vscode.window.showErrorMessage(
          `Loom server health check failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    }
  );

  // Register configuration change listener
  vscode.workspace.onDidChangeConfiguration((event) => {
    if (event.affectsConfiguration('loom')) {
      const config = vscode.workspace.getConfiguration('loom');
      const newServerUrl =
        config.get<string>('serverUrl') || 'http://localhost:8787';
      const newApiKey =
        config.get<string>('apiKey') || process.env.LOOM_API_KEY || '';

      loomClient = new LoomClient(newServerUrl, newApiKey);
      outputChannel.appendLine('[Config] Loom settings updated');
    }
  });

  // Add commands to context
  context.subscriptions.push(
    searchCommand,
    deepCommand,
    reframeCommand,
    healthCommand,
    statusBarItem,
    outputChannel
  );

  // Perform initial health check
  try {
    await loomClient.checkHealth();
    statusBarItem.text = '$(check) Loom: Ready';
  } catch {
    statusBarItem.text = '$(error) Loom: Not Connected';
  }
}

export function deactivate() {
  outputChannel.dispose();
  statusBarItem.dispose();
}

function getLoadingHtml(): string {
  return `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
          }
          .spinner {
            border: 4px solid var(--vscode-textBlockQuote-border);
            border-top: 4px solid var(--vscode-focusBorder);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
          }
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        </style>
      </head>
      <body>
        <div class="spinner"></div>
      </body>
    </html>
  `;
}

function getDeepResearchHtml(results: any): string {
  const resultsHtml = Array.isArray(results)
    ? results
        .map(
          (result: any, index: number) => `
        <div class="result">
          <h3>${index + 1}. ${result.title || 'Untitled'}</h3>
          ${result.url ? `<p><strong>URL:</strong> <a href="${result.url}" target="_blank">${result.url}</a></p>` : ''}
          ${result.snippet ? `<p>${result.snippet}</p>` : ''}
          ${result.content ? `<pre>${escapeHtml(result.content.substring(0, 500))}</pre>` : ''}
        </div>
      `
        )
        .join('')
    : `<p>No results found</p>`;

  return `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            padding: 20px;
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            line-height: 1.6;
          }
          .container {
            max-width: 900px;
            margin: 0 auto;
          }
          h1 {
            color: var(--vscode-focusBorder);
            border-bottom: 2px solid var(--vscode-textBlockQuote-border);
            padding-bottom: 10px;
          }
          .result {
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid var(--vscode-focusBorder);
            background: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 4px;
          }
          .result h3 {
            margin-top: 0;
            color: var(--vscode-focusBorder);
          }
          .result p {
            margin: 10px 0;
          }
          .result a {
            color: var(--vscode-textLink-foreground);
            text-decoration: none;
          }
          .result a:hover {
            text-decoration: underline;
          }
          pre {
            background: var(--vscode-editorCodeLens-foreground);
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Deep Research Results</h1>
          ${resultsHtml}
        </div>
      </body>
    </html>
  `;
}

function escapeHtml(text: string): string {
  const map: { [key: string]: string } = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (char) => map[char]);
}
