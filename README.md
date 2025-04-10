# AWSドキュメントリンク収集・NotebookLM登録ツール

このリポジトリには、AWSドキュメントからリンクを抽出し、Google NotebookLMにそれらのリンクを効率的に追加するためのツールが含まれています。

## 機能概要

1. **AWSドキュメントリンク抽出ツール** (`aws_doc_link_scraper.py`)
   - AWSドキュメントページからナビゲーションメニューのリンクを抽出
   - 結果をファイルに保存（デフォルト: `aws_links.txt`）

2. **NotebookLMアップローダーツール** (`notebook_lm_uploader.py`)
   - Google NotebookLMへのURLの自動追加
   - 複数のURLを一括で追加可能
   - 追加するURLの範囲指定が可能

## 前提条件

- 以下のパッケージがインストールされていること：
  - playwright
  - beautifulsoup4

## インストール方法

```bash
# 仮想環境を作成（推奨）
python -m venv .venv
source .venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt

# Playwrightのブラウザをインストール
playwright install chromium
```

## 使用方法

### 1. AWSドキュメントからリンクを抽出

```bash
python aws_doc_link_scraper.py --url "https://docs.aws.amazon.com/[サービス名]/latest/[ドキュメント種類]/" --output aws_links.txt
```

引数:

- `--url` (必須): 抽出するAWSドキュメントページのURL
- `--output` (オプション): 結果を保存するファイル名（デフォルト: `aws_links.txt`）

### 2. NotebookLMにリンクを追加

```bash
python notebook_lm_uploader.py --url "https://notebooklm.google.com/[ノートブックID]" --file aws_links.txt --start 1 --end 5 --max 5
```

引数:

- `--url` (必須): NotebookLMのURL
- `--file` (オプション): URLリストが含まれるファイルのパス（デフォルト: `aws_links.txt`）
- `--start` (オプション): 追加するURLの開始番号（1から始まる、デフォルト: 1）
- `--end` (オプション): 追加するURLの終了番号
- `--max` (オプション): 一度に追加するURLの最大数

## 動作の流れ

1. `aws_doc_link_scraper.py` を実行してAWSドキュメントからリンクを抽出
2. 抽出されたリンクは `aws_links.txt` に保存される
3. `notebook_lm_uploader.py` を実行してNotebookLMに選択したリンクを追加
4. NotebookLMへのログインが必要な場合は手動でログイン
5. リンクの追加は自動的に行われる
