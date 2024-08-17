from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

def train_field_matching_model():
    sample_data = [
        ("opt-in","opt in"),
        ("first-name", "first name"),
        ("last-name", "last name"),
        ("complete name", "name"),
        ("full name", "name"),
        ("full-name", "name"),
        ("email", "email"),
        ("email address", "email"),
        ("email-address", "email"),
        ("password","password"),
        ("pin","pin"),
        ("telephone","phone"),
        ("cell #", "phone"),
        ("phone number", "phone"),
        ("phone-number", "phone"),
        ("phone_type","phone_type"),
        ("address 1", "address 1"),
        ("address 2", "address 2"),
        ("address-1", "address 1"),
        ("address-2", "address 2"),
        ("zip", "zip"),
        ("zip code", "zip"),
        ("postal code", "zip"),
        ("city","city"),
        ("state","state"),
        ("license-state","state"),
        ("country","country"),
        ("abbreviated-country", "country"),
        ("Home address", "address"),
        ("residential address", "address"),
        ("mailing address", "address"),
        ("home-address", "address"),
        ("residence", "address"),
        ("ssn", "ssn"),
        ("social security number", "ssn"),
        ("social-security-number", "ssn"),
        ("birthday","birthday"),
        ("dob", "date of birth"),
        ("dob-formatted","dob-formatted"),
        ("birth date", "date of birth"),
        ("birthdate", "date of birth"),
        ("birth-date", "date of birth"),
        ("date of birth", "date of birth"),
        ("gender", "gender"),
        ("drivers license number", "drivers-license-number"),
        ("license number", "drivers-license-number"),
        ("drivers-license-number", "drivers-license-number"),
        ("license", "drivers-license-number"),
        ("license-#", "drivers-license-number"),
        ("drivers license #", "drivers-license-number"),
        ("submit", "submit button"),
        ("confirm", "submit button"),
        ("income","income"),
        ("employment-status","employment-status"),
        ("occupation","occupation"),
        ("rent","rent"),
        ("terms_conditions", "terms & conditions"),
        ("captcha","captcha"),
        ("ssa-verification","ssa-verification"),
        ("paperless","paperless"),
        ("citizen","citizen"),
        ("secondary-citizen","secondary-citizen"),
        ("bank-account","bank-account")
    ]
    texts, labels = zip(*[(desc, field) for field, *descriptions in sample_data for desc in descriptions])
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(texts)
    model = LogisticRegression()
    model.fit(X, labels)
    return model, vectorizer

async def advanced_field_matching(page, model, vectorizer):
    elements = await page.query_selector_all("input")
    fields = {}
    for element in elements:
        placeholder = await element.get_attribute("placeholder") or ""
        label = await element.get_attribute("label") or ""
        text = placeholder + " " + label
        if text.strip():
            prediction = model.predict(vectorizer.transform([text]))[0]
            fields[prediction] = element
    return fields
