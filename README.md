# Twilio Call Monitor

自動的にTwilioのコールログを監視し、長時間通話や進行中の通話を検知してメール通知を行うGitHub Actionsワークフロー。

## 機能

- 5分おきにTwilioのコールログを確認
- 10分以上続いている通話を検知
- 現在進行中の通話を検知
- 検知した通話があれば、SendGridを使用してメール通知を送信

## セットアップ手順

### 1. リポジトリの準備

このリポジトリをGitHubにプッシュします。

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 2. シークレットの設定

GitHubリポジトリの「Settings」→「Secrets」→「Actions」から以下のシークレットを設定します：

- `TWILIO_ACCOUNT_SID`: TwilioのアカウントSID
- `TWILIO_AUTH_TOKEN`: Twilioの認証トークン
- `SENDGRID_API_KEY`: SendGridのAPIキー
- `NOTIFICATION_EMAIL`: 通知を受け取るメールアドレス
- `FROM_EMAIL`: 通知の送信元メールアドレス（SendGridで認証済みのアドレス）

### 3. GitHub Actionsの有効化

リポジトリの「Actions」タブからワークフローを有効化します。

## ローカルでのテスト

ローカル環境でテストする場合は、以下の手順に従います：

1. 必要なパッケージをインストール：
   ```bash
   pip install -r requirements.txt
   ```

2. 環境変数を設定：
   ```bash
   export TWILIO_ACCOUNT_SID="your_account_sid"
   export TWILIO_AUTH_TOKEN="your_auth_token"
   export SENDGRID_API_KEY="your_sendgrid_api_key"
   export NOTIFICATION_EMAIL="your_email@example.com"
   export FROM_EMAIL="from_email@example.com"
   ```

3. スクリプトを実行：
   ```bash
   python monitor_calls.py
   ```

## カスタマイズ

- 監視の頻度を変更する場合は、`.github/workflows/monitor-calls.yml`のcron式を編集してください。
- 長時間通話の閾値を変更する場合は、`monitor_calls.py`の`LONG_CALL_THRESHOLD`を編集してください。