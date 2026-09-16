# Japan Hunt v0.5

海外ユーザーの日本商品への購入需要を収集し、日本国内の商品情報と突き合わせてOpportunity Scoreを算出するMVP。

## v0.5 changes

- RedditのHTTP 429や一時エラーで全体停止しない
- Google News RSSを第2の需要ソースとして追加
- RedditとGoogle Newsを同じ需要クラスタへ集約
- `spikes` のスコープバグを修正
- eBay価格取得失敗時の未初期化変数バグを修正
- 価格取得失敗時もCSV生成を継続
- GitHub Actionsの `contents: write` 権限を明示
- X/Redditへの自動投稿はまだ行わない

Google News RSSは検索クエリ単位で取得し、英語圏（US）の検索結果を使います。
Google News RSSの検索URL形式は一般に `news.google.com/rss/search?q=...` が使われます。
公式Google Search資料でもRSS/AtomがURL発見に使われる仕組みが説明されています。

## 実行

```bash
pip install -r requirements.txt
python main.py
```

生成:
- `data/japan_hunt.db`
- `data/opportunities.csv`
- `data/demand_history.json`
- `data/price_cache.json`

## GitHub Actions

`.github/workflows/daily.yml` が6時間ごとに実行します。
`workflow_dispatch` で手動実行もできます。

GitHub Actionsからリポジトリへレポートを書き戻すため、workflow内で
`permissions: contents: write` を設定しています。

## 価格データについて

eBay公開検索ページから表示価格を取得し、1 USD = 150 JPYの暫定換算でPrice Gapを計算します。
これは成約価格ではなく、検索結果に表示される出品価格の中央値です。

## 安全設計

- Reddit取得失敗 → Newsへ継続
- News取得失敗 → 商品取得へ継続
- eBay取得失敗 → 前回キャッシュまたは価格差なしで継続
- Pokémon Centerの商品取得件数異常 → 安全停止
- まだ自動投稿しない

## 次の段階

1. 数日間GitHub Actionsを回してデータ蓄積
2. 誤マッチを確認
3. Opportunity Scoreを調整
4. ZenMarketアフィリエイト導線を追加
5. 投稿候補を人間確認
6. 十分な精度が出たらSNS自動投稿を検討
