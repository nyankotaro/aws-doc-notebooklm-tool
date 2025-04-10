from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import os
import argparse

# コマンドライン引数の設定
parser = argparse.ArgumentParser(description='AWSドキュメントページのリンクを抽出します')
parser.add_argument('--url', type=str, required=True,
                    help='抽出するAWSドキュメントページのURL (必須)')
parser.add_argument('--output', type=str, default='aws_links.txt',
                    help='結果を保存するファイル名（デフォルト: aws_links.txt）')
args = parser.parse_args()

# AWSドキュメントページのURL
url = args.url

# Playwrightを使用してページを取得
def get_page_html(url):
    print(f"ページにアクセス中: {url}")
    with sync_playwright() as p:
        # ヘッドレスモードでブラウザを起動
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # ページにアクセス
            page.goto(url)
            
            # ページが完全にロードされるまで待機
            page.wait_for_load_state('networkidle')
            print("ページが完全にロードされました")
            
            # HTMLを取得
            html_content = page.content()
            
            return html_content
        finally:
            # ブラウザを閉じる
            browser.close()

# ページのHTMLを取得
print("Playwrightを使用してHTMLを取得しています...")
html_content = get_page_html(url)
print("HTMLの取得が完了しました")

# BeautifulSoupでHTMLを解析
print("BeautifulSoupでHTMLを解析しています...")
soup = BeautifulSoup(html_content, 'html.parser')

# 結果を保存するファイル名
output_file = args.output

# 左ペインのリンクを抽出
print("ナビゲーションメニューからリンクを抽出しています...")
# AWSドキュメントの左側のナビゲーションは通常 data-testid="doc-page-toc" の属性を持つdiv内にある
nav_div = soup.find('div', {'data-testid': 'doc-page-toc'})

# ファイルに書き込むための準備
with open(output_file, "w", encoding="utf-8") as f:
    if nav_div:
        # すべてのリンクを抽出
        links = nav_div.find_all('a', href=True)
        
        # ベースURLを取得（相対URLを絶対URLに変換するため）
        base_url = '/'.join(url.split('/')[:-1]) + '/'
        
        print(f"\n合計 {len(links)} 個のリンクが見つかりました\n")
        
        # リンクとそのテキストを表示とファイルへの書き込み
        for i, link in enumerate(links, 1):
            href = link['href']
            # 相対URLを絶対URLに変換
            if not href.startswith('http'):
                full_url = base_url + href
            else:
                full_url = href
                
            # リンクテキストを取得（spanタグ内にある場合が多い）
            link_text = link.get_text(strip=True)
            # コンソールには詳細情報を表示
            link_info = f"{i}. {link_text}: {full_url}"
            print(link_info)
            # ファイルには項番とURLのみ記録
            f.write(f"{i}. {full_url}\n")
    else:
        error_msg = "ナビゲーションメニューが見つかりませんでした。セレクタを確認してください。"
        print(error_msg)
        f.write(error_msg + "\n")
    
print(f"\n処理が完了しました。結果は {os.path.abspath(output_file)} に保存されました。")