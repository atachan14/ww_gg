# Initial7 full-result attempt under a 120-second worker cap

Exactly one new-route attempt was made on the same initial7 UNIFORM input, with deferred diagnostics enabled. Code baseline was 1a8974c. The worker had a 1,500,000,000-byte guard and an external 120-second process timeout. The calculation budget was115 seconds, reserving five seconds for atomic checkpoint persistence, retained-object census and shutdown. No old independent worker or additional new attempt was run.

## Outcome and limits

The initial Forecast did not finish. The cooperative calculation budget stopped at115.000 seconds, work147,635. A complete final atomic checkpoint, including the last exact (Board,Q,past,P,observer,physical) input and the retained-object census, was saved at116.082954 seconds. Peak saved working set was1,183,526,912 bytes, below1.5GB. No structural Pending/refusal was recorded in the reached search; that does not prove all future branches are supported.

The worker had not exited by the external120-second timeout and subprocess.run stopped it (supervisor wall120.095323 seconds, including timeout/termination overhead). This is distinct from the saved115-second calculation stop. The exact checkpoint was already on disk. A subsequent read-only process check showed no new trial Python process remaining. The controller's timeout readback now preserves both saved calculation status and external process termination status rather than obscuring the earlier stop. No retry was made to change this outcome.

Raw evidence: initial7-120-new-trial.json and initial7-120-comparison.json. The snapshot includes root saved inputs, full last exact input state, last Board/history, first_refusal=null, detailed counters, comparison completion flags and identity census. It is not a serialized entire cache/call stack or a resumable worker image.

## Reached work

- Completed scalar values:69,455.
- Scalar actions:208,544; recorded action evaluations:208,548.
- Generated source/Board requests:98,831.
- Terminal diagnostic recipe records:198,443; all branch recipes:208,548.
- Publication laws:5,884; pattern representatives:55,801; named public vectors:57,238.
- Last solve Board:day3, living1/3/4, after execute5, bite6, execute2, bite7. The full Q/P/acquisition/report state is in the raw checkpoint.

Retained-object identity census (named engine structures only, not a whole-heap count):89,484 tracked Board objects;143,330 joint law objects;307,708 joint hypothesis objects;507,679 identity-hash entries;96,155 unique saved requests;96,163 evidence operations;94,431 frozen kernel objects. There were10,105 retained resolution entries/full outcome objects, zero expanded diagnostic outcome references,208,548 lightweight deferred recipe inputs and zero diagnostic materializations. Generated source keys are not the number of unique Board instances.

## Comparison completion scope

| Requested output | Completed in this attempt? |
| --- | --- |
| Initial Forecast with all action/dawn values | No |
| Complete Table | No |
| Joint-selection mass comparison | No |
| Full labelled branch/terminal mass comparison | No |
| Representative independent cold validation | No |
| Old independent reference worker | Not started: new result incomplete |

No initial7 speedup, completion or full semantic equivalence is claimed. Earlier finite-case equality and short matched-work memory comparisons remain separate evidence. This attempt changed no normal UI, HELP, MAX, public edition or shared solver source; no server was restarted, and nothing was pushed/deployed.

## 朝に引き継ぐ未完課題

初期7人UNIFORMの全結果は未取得。遅延診断を有効にした1回の試行は計算115秒で停止し、69,455状態・208,544行動・98,831生成Boardまで到達、最大1.184GB。到達範囲に未保証条件は記録されなかったが、Table/joint/枝mass/代表coldの全体比較には進めていない。旧独立と再試行は行っていない。

次の構造課題は、終端支払いを計算する共通フローで、継続に不要な完全Board・公開文脈を毎回構築する負担を減らし、必要な詳細を正確な履歴から復元すること。終端レシピが約95%を占めるため、枝を削らずに同じ支払いを返す軽量な終端経路を小ケースで検証する価値がある。取得ルール・本人支持・観測整合性の検証は維持する。並行して、同一の完全な不変データの共有と証明kernelの設定／キャッシュ分離が保持量の課題として残る。これらは候補であり、今回実装・性能検証したものではない。