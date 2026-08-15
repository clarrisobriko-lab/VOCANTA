from automation.upload_hardening import classify_upload_label, choose_upload, validate_upload_path


def test_upload_labels_are_classified():
    assert classify_upload_label("Upload your CV") == "cv"
    assert classify_upload_label("Cover Letter") == "cover_letter"
    assert classify_upload_label("Additional supporting document") == "supporting"


def test_unknown_upload_defaults_to_cv():
    assert classify_upload_label("Attach file") == "cv"


def test_missing_optional_document_is_not_replaced_with_cv():
    plan = choose_upload("Cover Letter", resume_path="cv.pdf", cover_letter_path="")
    assert plan is None


def test_valid_upload_path(tmp_path):
    document = tmp_path / "cv.pdf"
    document.write_bytes(b"%PDF-test")
    assert validate_upload_path(str(document)) == (True, "ok")


def test_missing_upload_path_is_rejected(tmp_path):
    valid, reason = validate_upload_path(str(tmp_path / "missing.pdf"))
    assert valid is False
    assert "does not exist" in reason
