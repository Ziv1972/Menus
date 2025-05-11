
import streamlit as st
import pandas as pd
from difflib import SequenceMatcher

st.set_page_config(page_title="Institutional Menu Checker", layout="wide")
st.title("📄 Institutional Lunch Menu Checker")

st.markdown("""Upload a **menu file** (Excel) and a **rules file** with frequency and keyword conditions.
The system will highlight frequency violations based on your definitions, including customized matching rules (e.g., 'chicken wings', 'stuffed chicken', 'tabit').""")

menu_file = st.file_uploader("Upload Menu Excel File", type="xlsx", key="menu")
rules_file = st.file_uploader("Upload Rules Excel File", type="xlsx", key="rules")

if menu_file and rules_file:
    with st.spinner("Processing data..."):
        menu_xls = pd.ExcelFile(menu_file)
        rules_xls = pd.ExcelFile(rules_file)

        min_freq_df = rules_xls.parse("תדירות מינימלית")
        min_freq_df.columns = min_freq_df.iloc[0]
        min_freq_df = min_freq_df.drop([0, 1, 2]).dropna(subset=["סוג"])

        all_weeks_df = pd.DataFrame()
        for sheet in menu_xls.sheet_names:
            df = menu_xls.parse(sheet)
            df.columns = df.iloc[1]
            df = df.drop([0, 1])
            all_weeks_df = pd.concat([all_weeks_df, df], ignore_index=True)

        day_cols = [c for c in all_weeks_df.columns if "יום" in str(c)]
        for col in day_cols:
            all_weeks_df[col] = all_weeks_df[col].astype(str).str.replace("❌", "").str.strip()

        actual_dishes = pd.Series(all_weeks_df[day_cols].values.ravel()).dropna().str.strip().str.lower()

        def fuzzy_match(k, dish):
            return SequenceMatcher(None, k, dish).ratio() >= 0.85

        def get_keywords(row):
            keywords = set()
            for col in ["מלל חלופי", "יכול להופיע כ", "דוגמאות מהתפריט"]:
                if pd.notna(row.get(col)):
                    keywords.update(x.strip().lower() for x in str(row[col]).split("/"))
            keywords.add(str(row["סוג"]).strip().lower())
            return list(keywords)

        # כללים מותאמים אישית לפי אישור המשתמש
        custom_equivalents = {
            "שיפודי כנפיים עם ירקות גריל": ["כנפיים"],
            "עופות שלמים בגריל": ["עוף שלם", "עופות שלמים"],
            "טבית עופות צלויים עם אורז ובהרט": ["טבית"],
            "סלט אבוקדו": ["אבוקדו"],
            "סלט פטריות אסייתי": ["פטריות אסייתי", "פטריות אסייאתי"],
    "שניצל עוף פריך": ["שניצל"],
    "חזה עוף בגריל": ["חזה עוף"],
    "המבורגר בקר": ["המבורגר"],
    "קציצות בקר ברוטב": ["קציצות בשר ברוטב אדום על קוסקוס", "קציצות ברוטב אדום פיקנטיי"],
    "בקלוואת בשר": ["בקלאוות בשר מדפי פילו בסגנון סוכריה"],
    "ממולאים קטנים": [
        "פרגית ממולאת אורז לצד ירקות צלויים",
        "פילה פילו ממולא בתערובת בשר עגל",
        "חציל ממולא",
        "עלי גפן ממולאים"
    ],
        }

        def count_matches(keywords, series, original_name):
            count = 0
            for dish in series:
                dish = dish.strip().lower()

                # התאמה לפי כלל מותאם אישי
                for rule_name, rule_keywords in custom_equivalents.items():
                if any(trigger in name for trigger in [rule_name]) or any(trigger in name for trigger in rule_keywords):
                    if any(custom_kw in dish for custom_kw in rule_keywords):
                        count += 1
                        break

                    if any(custom_kw in dish for custom_kw in custom_equivalents[original_name]):
                        count += 1
                        continue

                # התאמה מלאה
                if dish in keywords:
                    count += 1
                    continue

                # התאמה לפי לפחות שתי מילים מתוך הרשימה
                if sum(1 for k in keywords if k in dish) >= 2:
                    count += 1
                    continue

                # מילה אחת מתוך הרשימה
                if len(keywords) == 1 and any(k in dish for k in keywords):
                    count += 1
                    continue

                # התאמה fuzzy
                if any(fuzzy_match(k, dish) for k in keywords):
                    count += 1
            return count

        report = []
        for _, row in min_freq_df.iterrows():
            name = str(row["סוג"]).strip()
            keywords = get_keywords(row)
            required = row.get("בחודש") or row.get("בשבוע")
            try:
                required = int(required) if row.get("בחודש") else int(required) * 5
            except:
                continue
            actual = count_matches(keywords, actual_dishes, name)
            if actual < required:
                report.append({
                    "Dish Type": name,
                    "Required": required,
                    "Actual Found": actual,
                    "Gap": required - actual
                })

        result_df = pd.DataFrame(report)

    st.success("Menu check completed.")
    st.dataframe(result_df, use_container_width=True)
    st.download_button("Download CSV Report", result_df.to_csv(index=False).encode("utf-8"), file_name="menu_report.csv")
