from app.ai.alignment import align_words, normalize_arabic_word


def test_normalize_common_arabic_variants():
    assert normalize_arabic_word("أَعُوذُ") == normalize_arabic_word("اعوذ")
    assert normalize_arabic_word("ٱلرَّحْمَٰنِ") == normalize_arabic_word("الرحمن")
    assert normalize_arabic_word("عَلَيْهِ") == normalize_arabic_word("عليه")


def test_identical_text_has_no_issues():
    result = align_words("بسم الله الرحمن الرحيم", "بسم الله الرحمن الرحيم")

    assert result.expected_word_count == 4
    assert result.recognized_word_count == 4
    assert result.matched_word_count == 4
    assert result.issues == []


def test_detects_missing_word():
    result = align_words("بسم الله الرحمن الرحيم", "بسم الله الرحيم")

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.operation == "deletion"
    assert issue.expected_word == "الرحمن"
    assert issue.recognized_word is None
    assert issue.expected_index == 2


def test_detects_extra_word():
    result = align_words("بسم الله الرحيم", "بسم الله الرحمن الرحيم")

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.operation == "insertion"
    assert issue.expected_word is None
    assert issue.recognized_word == "الرحمن"
    assert issue.recognized_index == 2


def test_detects_substituted_word():
    result = align_words("بسم الله الرحيم", "بسم بالله الرحيم")

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.operation == "substitution"
    assert issue.expected_word == "الله"
    assert issue.recognized_word == "بالله"
    assert issue.expected_index == 1
    assert issue.recognized_index == 1


def test_returns_original_words_in_issues():
    result = align_words("الرَّحْمَٰنِ", "الرَّحِيمِ")

    assert result.issues[0].expected_word == "الرَّحْمَٰنِ"
    assert result.issues[0].recognized_word == "الرَّحِيمِ"


def test_empty_texts():
    result = align_words("", "")

    assert result.expected_word_count == 0
    assert result.recognized_word_count == 0
    assert result.matched_word_count == 0
    assert result.issues == []


def test_empty_recognition_marks_all_expected_words_missing():
    result = align_words("بسم الله", "")

    assert result.matched_word_count == 0
    assert [issue.operation for issue in result.issues] == [
        "deletion",
        "deletion",
    ]


def test_handles_multiple_issues_in_one_alignment():
    result = align_words(
        "بسم الله الرحمن الرحيم",
        "بسم الرحمن الرحيم زيادة",
    )

    assert [issue.operation for issue in result.issues] == [
        "deletion",
        "insertion",
    ]
    assert result.issues[0].expected_word == "الله"
    assert result.issues[1].recognized_word == "زيادة"


def test_handles_repeated_words():
    result = align_words(
        "الله الله الرحمن",
        "الله الرحمن",
    )

    assert len(result.issues) == 1
    assert result.issues[0].operation == "deletion"
    assert result.issues[0].expected_word == "الله"
    assert result.issues[0].expected_index == 1


def test_ignores_attached_arabic_punctuation():
    result = align_words(
        "بسم الله، الرحمن الرحيم.",
        "بسم الله الرحمن الرحيم",
    )

    assert result.issues == []
    assert result.matched_word_count == 4


def test_ignores_quranic_end_of_ayah_marker_attached_to_word():
    result = align_words(
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ۝",
        "الحمد لله رب العالمين",
    )

    assert result.issues == []
    assert result.matched_word_count == 4


def test_ignores_standalone_quranic_end_of_ayah_marker():
    result = align_words(
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ ۝",
        "الحمد لله رب العالمين",
    )

    assert result.issues == []
    assert result.matched_word_count == 4


def test_normalization_preserves_non_punctuation_symbols():
    assert normalize_arabic_word("كلمة🙂") == "كلمة🙂"


def test_normalization_ignores_arabic_diacritics():
    assert normalize_arabic_word("الرَّحْمَٰنِ") == "الرحمن"


def test_normalization_preserves_original_text_in_alignment():
    expected = "الرَّحْمَٰنِ"
    recognized = "الرَّحِيمِ"

    result = align_words(expected, recognized)

    assert len(result.issues) == 1
    assert result.issues[0].expected_word == expected
    assert result.issues[0].recognized_word == recognized
