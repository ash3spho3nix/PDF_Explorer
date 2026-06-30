from classifier.rules import RuleClassifier


def test_classify_file_by_filename(simple_pdffile):
    pdf = simple_pdffile
    pdf.filename = "gst_invoice_2026.pdf"
    category, confidence, debug_info = RuleClassifier().classify(pdf, "")

    assert category == "Bill"
    assert confidence > 0.0
    assert "invoice" in debug_info["filename_matches"]


def test_classify_no_matches_returns_unknown(simple_pdffile):
    pdf = simple_pdffile
    pdf.filename = "randomfilename.pdf"
    pdf.title = None
    pdf.author = None
    pdf.subject = None
    pdf.keywords = None

    category, confidence, debug_info = RuleClassifier().classify(pdf, "")

    assert category == "Unknown"
    assert confidence == 0.0
    assert debug_info["filename_matches"] == []


def test_add_rule_increases_confidence(simple_pdffile):
    classifier = RuleClassifier()
    classifier.add_rule("Custom", ["customword"], weight=1.0)

    pdf = simple_pdffile
    pdf.filename = "customword.pdf"

    category, confidence, debug_info = classifier.classify(pdf, "")

    assert category == "Custom"
    assert confidence > 0.0
    assert "customword" in debug_info["filename_matches"]
