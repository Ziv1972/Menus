
import streamlit as st
import pandas as pd
from difflib import SequenceMatcher

st.set_page_config(page_title="בודק תפריטים מוסדיים", layout="wide")
st.title("📄 מערכת בדיקת תפריטי צהריים")

st.markdown("""
העלה קובץ **תפריט** (לפי שבועות או חודש) וכן קובץ **התניות ומגבלות**.
המערכת תבצע בדיקות תדירות והתאמות לפי ההגדרות, כולל סימון חריגות.
""")

menu_file = st.file_uploader("בחר קובץ תפריט (Excel)", type="xlsx", key="menu")
rules_file = st.file_uploader("בחר קובץ התניות ומגבלות (Excel)", type="xlsx", key="rules")

if menu_file and rules_file:
    with st.spinner("קורא נתונים..."):
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

        def get_keywords(row):
            keywords = set()
            for col in ["מלל חלופי", "יכול להופיע כ", "דוגמאות מהתפריט"]:
                if pd.notna(row.get(col)):
                    keywords.update(x.strip().lower() for x in str(row[col]).split("/"))
            return list(keywords) if keywords else [str(row["סוג"]).strip().lower()]

        def fuzzy_match(k, dish):
            return SequenceMatcher(None, k, dish).ratio() >= 0.85

        def count_matches(keywords, series):
            count = 0
            for dish in series:
                if dish in keywords:
                    count += 1
                    continue
                if sum(1 for k in keywords if k in dish) >= 2:
                    count += 1
                    continue
                if len(keywords) == 1 and any(k in dish for k in keywords):
                    count += 1
                    continue
                if any(fuzzy_match(k, dish) for k in keywords):
                    count += 1
            return count

        report = []
        for _, row in min_freq_df.iterrows():
            name = str(row["סוג"]).strip()
            keywords = get_keywords(row)
            req = row.get("בחודש") or row.get("בשבוע")
            try:
                required = int(req) if row.get("בחודש") else int(req) * 5
            except:
                continue
            actual = count_matches(keywords, actual_dishes)
            if actual < required:
                report.append({"מנה": name, "נדרש": required, "הופיע בפועל": actual, "פער": required - actual})

        result_df = pd.DataFrame(report)

    st.success("הבדיקה הושלמה!")
    st.dataframe(result_df, use_container_width=True)
    st.download_button("הורד דו"ח Excel", result_df.to_csv(index=False).encode("utf-8"), file_name="דו"ח תדירות.csv")
