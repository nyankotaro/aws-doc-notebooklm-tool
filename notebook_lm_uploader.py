from playwright.sync_api import sync_playwright
import time
import re
import argparse

def extract_urls_from_file(file_path):
    """ファイルからURLを抽出する関数"""
    urls = []
    url_pattern = re.compile(r'https?://[^\s]+')
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 行の番号とURLを分離
            parts = line.strip().split('. ', 1)
            if len(parts) == 2:
                # URLを抽出
                match = url_pattern.search(parts[1])
                if match:
                    urls.append(match.group(0))
    
    return urls

def add_urls_to_notebooklm(notebook_url, urls_to_add, max_urls=5):
    """Playwrightを使用してNotebookLMにURLを追加する関数"""
    print("Playwrightを起動しています...")
    
    # 学習結果を格納する辞書（セッション内でのみ有効）
    learned_selectors = {
        "add_source_btn": None,
        "website_option": None,
        "url_input": None,
        "insert_btn": None
    }
    
    # 待機時間の設定 - 実行環境に応じて調整可能
    wait_times = {
        "click_before": 0.2,     # クリック前の待機（秒）
        "click_after": 0.3,      # クリック後の短い待機（秒）
        "insert_after": 0.3,     # 挿入後の待機（秒）- さらに短縮
        "next_url": 0.5          # 次のURL追加前の待機（秒）- さらに短縮
    }
    
    # 並行処理モードを有効にする設定
    parallel_mode = {
        "enabled": True,          # 並行処理を有効にする
        "prepare_next": True,     # 処理完了を待たずに次のURLの準備を開始
        "max_check_time": 0.8     # URL追加確認の最大時間（秒）
    }
    
    with sync_playwright() as p:
        # ブラウザ起動（ヘッドレスモードをオフに）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # NotebookLMにアクセス
            print(f"NotebookLM ({notebook_url}) にアクセスしています...")
            page.goto(notebook_url)
            print("アクセス完了")
            
            # ログイン画面が表示される場合はログインを待つ
            print("Googleアカウントでのログインが必要な場合は、手動でログインしてください...")
            print("ログイン後に処理を続行します（最大120秒待機）")
            
            # NotebookLMのインターフェース検出 - プロジェクトタイトル要素で検出
            print("NotebookLMのインターフェースを待機しています...")
            try:
                # プロジェクトタイトル要素を待機 - NotebookLMの特徴的な要素
                page.wait_for_selector('editable-project-title', timeout=120000)
                print("NotebookLMのインターフェースが読み込まれました")
            except Exception as e:
                print("プロジェクトタイトルが見つかりませんでした。代替の要素を検索します...")
                try:
                    # ソースタブをフォールバックとして検索
                    source_tab_selector = "div:has-text('ソース'), div:has-text('Source')"
                    page.wait_for_selector(source_tab_selector, timeout=30000)
                    print("NotebookLMのインターフェースが読み込まれました")
                except Exception as e2:
                    raise Exception("NotebookLMインターフェースの読み込みを検出できませんでした")
            
            # UIの完全な読み込みを待機（少し短く）
            time.sleep(0.5)
            
            # 追加するURLの数を制限
            urls_to_add = urls_to_add[:max_urls]
            
            # 「ソースを追加」ボタンのセレクタ定義
            # 言語に依存しないセレクタを優先
            add_source_btn_selectors = [
                "button:has-text('Add')",                        # 英語「Add」テキスト
                "button:has-text('追加')"                         # 日本語「追加」テキスト（フォールバック）
            ]
            
            # ウェブサイトオプションのセレクタ（言語依存しないセレクタを優先）
            website_option_selectors = [
                "span.mat-mdc-chip-action:has(mat-icon:has-text('web'))",  # ログから最も効果的
                "span:has-text('Website')",                                # 英語テキスト
                "span:has-text('ウェブサイト')",                            # 日本語テキスト
                "div:has-text('Website')",                                # 英語テキスト
                "div:has-text('ウェブサイト')"                              # 日本語テキスト
            ]
            
            # 汎用的なウェブサイトセレクタ (選択オプションの確認用)
            general_website_selector = "span:has-text('ウェブサイト'), span:has-text('Website')"
            
            # URL入力フィールドのセレクタ（言語に依存しない技術的識別子を優先）
            url_input_selectors = [
                "input[formcontrolname='newUrl']",               # formcontrolname属性（Angular特有）
                "input[type='url']",                             # URL型入力フィールド
                "input.mat-mdc-input-element",                   # Material Design入力要素
                "div:has(mat-icon:has-text('web')) input",       # webアイコンを持つ親要素内の入力フィールド
                "div.mat-mdc-form-field-flex input",             # MDCフォームフィールド内の入力
                # 言語依存するセレクタはフォールバックとして最後に配置
                "div:has-text('URL') input",                     # URL文字列を含む親要素内の入力
                "div:has-text('Paste URL') input",               # 英語テキスト
                "div:has-text('URL を貼り付け') input"              # 日本語テキスト
            ]
            
            # 挿入ボタンのセレクタ（言語に依存しないセレクタを優先）
            insert_btn_selectors = [
                "button:has-text('Insert')",                       # 英語テキスト
                "button:has-text('挿入')"                           # 日本語テキスト
            ]
            
            # URL追加完了の検出用セレクタ
            url_added_selectors = [
                # ダイアログが閉じたことを検出
                ".mat-dialog-container:not([style*='visibility: visible'])",
                # リスト要素の変化を検出
                "div.source-list", 
                ".source-item", 
                ".mat-list-item", 
                ".url-item", 
                "ul li"
            ]
            
            # 次のURL追加処理の準備ができているか確認するセレクタ
            next_url_ready_selectors = [
                "button:has-text('Add')", 
                "button:has-text('追加')",
                "div.source-list"
            ]
            
            # 非同期チェックのための関数
            def is_element_present(selector, timeout=100):
                try:
                    # 非常に短いタイムアウトで要素の存在をチェック
                    return page.wait_for_selector(selector, timeout=timeout, state="attached") is not None
                except:
                    return False
            
            for i, url in enumerate(urls_to_add):
                print(f"URL {i+1}/{len(urls_to_add)} を追加中: {url}")
                
                # 最初のURLの場合のみウェブサイトオプションの表示を確認
                if i == 0:
                    # 1. まず最初にウェブサイトオプションが既に表示されているか確認
                    print("まずウェブサイトオプションが表示されているか確認します...")
                    website_option_visible = False
                    
                    # マテリアルデザインのチップ要素を探す
                    chip_selector = "mat-chip-option, mat-chip, .mdc-evolution-chip, .mat-mdc-chip"
                    try:
                        # 短いタイムアウトで待機（既に表示されている場合のみ検出）
                        if page.wait_for_selector(chip_selector, timeout=2000):
                            # さらにウェブサイトオプションが含まれているか確認
                            try:
                                if page.wait_for_selector(general_website_selector, timeout=1000):
                                    print("選択オプションメニューが既に表示されており、ウェブサイトオプションが見つかりました")
                                    website_option_visible = True
                                else:
                                    print("選択オプションメニューは表示されていますが、ウェブサイトオプションが見つかりません")
                                    website_option_visible = False
                            except:
                                print("選択オプションメニューは表示されていますが、ウェブサイトオプションが見つかりません")
                                website_option_visible = False
                    except:
                        print("選択オプションは表示されていません。「ソースを追加」から開始します")
                else:
                    # 2週目以降は常に「ソースを追加」から始める
                    website_option_visible = False
                    
                    # 次のURL追加の準備ができているか確認
                    ready_for_next = False
                    for selector in next_url_ready_selectors:
                        if is_element_present(selector):
                            ready_for_next = True
                            break
                    
                    if ready_for_next:
                        print("次のURL追加の準備ができています。処理を開始します")
                    else:
                        print("2週目以降のURL追加なので「ソースを追加」から処理を開始します")
                
                # ウェブサイトオプションが表示されていない場合は「ソースを追加」ボタンから処理
                if not website_option_visible:
                    # 「ソースを追加」ボタンをクリック
                    print("「ソースを追加」ボタンをクリックします...")
                    
                    # セクションやパネル、カード要素などを探す
                    source_section = page.query_selector("section, .mat-expansion-panel, mat-card, .section-container")
                    if not source_section:
                        print("汎用的なセクションが見つかりませんでした。ページ全体から検索します。")
                    
                    # 前回成功したセレクタがあれば最初に試す
                    if learned_selectors["add_source_btn"]:
                        try:
                            selector = learned_selectors["add_source_btn"]
                            btn = page.query_selector(selector)
                            if btn:
                                btn.scroll_into_view_if_needed()
                                time.sleep(wait_times["click_before"])
                                btn.click()
                                time.sleep(wait_times["click_after"])
                                goto_website_option = True
                            else:
                                goto_website_option = False
                        except Exception:
                            goto_website_option = False
                    else:
                        goto_website_option = False
                    
                    # 前回のセレクタが失敗した場合は通常の検索
                    if not goto_website_option:
                        add_btn_found = False
                        
                        # まずセクション内から検索
                        if source_section:
                            print("ソースセクションが見つかりました")
                            for selector in add_source_btn_selectors:
                                try:
                                    add_btn = source_section.query_selector(selector)
                                    if add_btn:
                                        add_btn.scroll_into_view_if_needed()
                                        time.sleep(wait_times["click_before"])
                                        add_btn.click()
                                        learned_selectors["add_source_btn"] = selector  # 成功したセレクタを記憶
                                        add_btn_found = True
                                        time.sleep(wait_times["click_after"])
                                        break
                                except Exception:
                                    continue
                        
                        # セクション内で見つからなかった場合、ページ全体から探す
                        if not add_btn_found:
                            print("セクション外でボタンを探します")
                            for selector in add_source_btn_selectors:
                                try:
                                    button = page.query_selector(selector)
                                    if button:
                                        button.scroll_into_view_if_needed()
                                        time.sleep(wait_times["click_before"])
                                        button.click()
                                        learned_selectors["add_source_btn"] = selector  # 成功したセレクタを記憶
                                        add_btn_found = True
                                        time.sleep(wait_times["click_after"])
                                        break
                                except Exception:
                                    continue
                        
                        # それでも見つからない場合はエラー
                        if not add_btn_found:
                            raise Exception("「ソースを追加」ボタンが見つかりませんでした")
                    
                    print("「ソースを追加」ボタンがクリックされました")
                    
                    # オプションメニューが表示されるまで待機
                    print("オプションメニューの表示を待機しています...")
                    try:
                        page.wait_for_selector(chip_selector, timeout=5000)
                        print("オプションメニューが表示されました")
                    except Exception:
                        print("標準的なチップメニューが見つかりませんでした、個別のオプションを探します")
                
                # ウェブサイトオプションをクリック
                print("ウェブサイトオプションを選択します...")
                
                # 前回成功したセレクタがあれば最初に試す
                website_option_found = False
                if learned_selectors["website_option"]:
                    try:
                        selector = learned_selectors["website_option"]
                        # 短いタイムアウトで待機
                        if page.wait_for_selector(selector, timeout=3000):
                            page.click(selector)
                            website_option_found = True
                            time.sleep(wait_times["click_after"])
                    except Exception:
                        pass
                
                # 前回のセレクタが失敗した場合は通常の検索
                if not website_option_found:
                    for selector in website_option_selectors:
                        try:
                            # やや短めのタイムアウトで待機
                            if page.wait_for_selector(selector, timeout=3000):
                                print(f"ウェブサイトオプションが見つかりました: {selector}")
                                page.click(selector)
                                learned_selectors["website_option"] = selector  # 成功したセレクタを記憶
                                website_option_found = True
                                time.sleep(wait_times["click_after"])
                                break
                        except Exception:
                            continue
                
                if not website_option_found:
                    print("より一般的なセレクタで再試行します")
                    try:
                        page.wait_for_selector(general_website_selector, timeout=10000)
                        page.click(general_website_selector)
                        time.sleep(wait_times["click_after"])
                        website_option_found = True
                    except Exception:
                        pass
                
                if not website_option_found:
                    raise Exception("ウェブサイトオプションが見つかりませんでした")
                
                print("ウェブサイトオプションを選択しました")
                
                # URLフィールドに入力
                print("URL入力フィールドを探しています...")
                
                # 前回成功したセレクタがあれば最初に試す
                url_input_found = False
                if learned_selectors["url_input"]:
                    try:
                        selector = learned_selectors["url_input"]
                        # より長めのタイムアウトで待機（ダイアログの表示に時間がかかる場合がある）
                        if page.wait_for_selector(selector, timeout=8000):
                            # フォーカスと入力
                            page.click(selector)
                            # 既存の内容をクリア
                            page.fill(selector, "")
                            # 新しいURLを入力
                            page.fill(selector, url)
                            url_input_found = True
                    except Exception:
                        pass
                
                # 前回のセレクタが失敗した場合は通常の検索
                if not url_input_found:
                    # まず、入力フィールドが表示されるまで少し待機（少し短く）
                    time.sleep(0.5)
                    
                    for selector in url_input_selectors:
                        try:
                            # より長めのタイムアウトで待機（ダイアログの表示に時間がかかる場合がある）
                            if page.wait_for_selector(selector, timeout=8000):
                                print(f"URL入力フィールドが見つかりました: {selector}")
                                # フォーカスと入力
                                page.click(selector)
                                # 既存の内容をクリア
                                page.fill(selector, "")
                                # 新しいURLを入力
                                page.fill(selector, url)
                                learned_selectors["url_input"] = selector  # 成功したセレクタを記憶
                                url_input_found = True
                                break
                        except Exception:
                            continue
                
                # もしそれでも失敗したら、キーボードショートカットを試す
                if not url_input_found:
                    print("キーボードショートカットを試みます")
                    try:
                        page.keyboard.press("Control+a")
                        page.keyboard.type(url)
                        url_input_found = True
                    except Exception:
                        pass
                
                if not url_input_found:
                    raise Exception("URL入力フィールドが見つかりませんでした")
                
                print(f"URL「{url}」を入力しました")
                
                # 挿入ボタンをクリック
                print("挿入ボタンを探しています...")
                
                # 前回成功したセレクタがあれば最初に試す
                insert_btn_found = False
                if learned_selectors["insert_btn"]:
                    try:
                        selector = learned_selectors["insert_btn"]
                        button = page.query_selector(selector)
                        if button:
                            # オーバーレイの問題を回避するためJavaScriptでクリック
                            page.evaluate("""(btn) => { btn.click(); }""", button)
                            insert_btn_found = True
                            # 最小限の待機（非常に短く）
                            time.sleep(wait_times["insert_after"])
                    except Exception:
                        pass
                
                # 前回のセレクタが失敗した場合は通常の検索
                if not insert_btn_found:
                    # 挿入ボタンが表示されるまで少し待機（短縮）
                    time.sleep(0.3)
                    
                    # まずJavaScriptを使用して直接クリックを試みる（オーバーレイ問題回避）
                    for selector in insert_btn_selectors:
                        try:
                            button = page.query_selector(selector)
                            if button:
                                print(f"挿入ボタンが見つかりました: {selector}")
                                # JavaScriptを使用してクリック（CDKオーバーレイの問題を回避）
                                page.evaluate("""(btn) => { btn.click(); }""", button)
                                learned_selectors["insert_btn"] = selector  # 成功したセレクタを記憶
                                insert_btn_found = True
                                # 最小限の待機（非常に短く）
                                time.sleep(wait_times["insert_after"])
                                break
                        except Exception:
                            continue
                
                # それでも失敗した場合、Enter キーを押して送信
                if not insert_btn_found:
                    print("Enterキーで送信を試みます")
                    try:
                        page.keyboard.press("Enter")
                        insert_btn_found = True
                        # 最小限の待機（非常に短く）
                        time.sleep(wait_times["insert_after"])
                    except Exception:
                        pass
                
                if not insert_btn_found:
                    raise Exception("挿入ボタンが見つからないかクリックできませんでした")
                
                print("挿入ボタンをクリックしました")
                
                # 追加完了の確認 - 非同期・効率的なアプローチ
                start_time = time.time()
                added_detected = False
                
                # URLが追加されたことを示す指標を監視
                while (time.time() - start_time) < parallel_mode["max_check_time"]:
                    # 短い間隔で各セレクタを迅速にチェック
                    for selector in url_added_selectors:
                        if is_element_present(selector):
                            added_detected = True
                            break
                    
                    if added_detected:
                        # 成功の兆候が見つかれば待機を中断
                        break
                    
                    # 短い間隔で再チェック
                    time.sleep(0.1)
                
                # 最低限の待機時間を確保
                remaining_time = wait_times["next_url"] - (time.time() - start_time)
                if remaining_time > 0:
                    time.sleep(remaining_time)
                
                print(f"URL {url} を追加しました")
            
            print(f"合計 {len(urls_to_add)} 個のURLが追加されました")
            
            print("処理が完了しました。ブラウザは自動的に閉じられません。")
            print("確認後、手動でブラウザを閉じてください。")
            
            # 自動で閉じない
            input("終了するには Enter キーを押してください...")
            
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
            # エラーが発生しても、ユーザーがブラウザを確認できるように待機
            input("エラーが発生しました。ブラウザを確認し、終了するには Enter キーを押してください...")
        finally:
            # ブラウザを閉じる
            browser.close()

def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='NotebookLMにURLを追加するツール')
    parser.add_argument('--url', type=str, required=True,
                        help='NotebookLMのURL（必須）')
    parser.add_argument('--file', type=str, default="aws_links.txt",
                        help='URLリストが含まれるファイルのパス')
    parser.add_argument('--start', type=int, default=1,
                        help='追加するURLの開始番号（1から始まる）')
    parser.add_argument('--end', type=int, default=None,
                        help='追加するURLの終了番号')
    parser.add_argument('--max', type=int, default=None,
                        help='一度に追加するURLの最大数')
    
    args = parser.parse_args()
    
    # 引数から値を取得
    notebook_url = args.url
    file_path = args.file
    start_index = args.start - 1  # 0ベースに変換
    end_index = args.end
    max_urls = args.max
    
    # ファイルからURLを抽出
    urls = extract_urls_from_file(file_path)
    
    if urls:
        # URLのフィルタリング（指定された範囲のみ）
        if start_index > 0 or end_index is not None:
            filtered_urls = urls[start_index:end_index]
            print(f"{len(filtered_urls)}個のURLが選択されました（{start_index + 1}番から{end_index if end_index else len(urls)}番まで）。")
        else:
            filtered_urls = urls
            print(f"{len(filtered_urls)}個のURLが抽出されました。")
        
        # NotebookLMにURLを追加
        if len(filtered_urls) > 0:
            add_urls_to_notebooklm(notebook_url, filtered_urls, max_urls=max_urls if max_urls else len(filtered_urls))
        else:
            print("選択された範囲にURLがありませんでした。")
    else:
        print("URLが見つかりませんでした。")

if __name__ == "__main__":
    main() 