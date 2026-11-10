import time

from workbench.classify import looks_english, predict, train


def test_department_accuracy(built):
    assert built["department"]["accuracy"] >= 0.85


def test_type_accuracy(built):
    assert built["type"]["accuracy"] >= 0.96


def test_predict_shape(built):
    pr = predict(built["department"]["model"], "Someone made payments on my card that I did not make and I think it is a scam.")
    assert pr.label == "Fraud claims" and 0 < pr.confidence <= 1
    assert 0 < len(pr.top_words) <= 5


def test_top_words_present_in_text(built):
    text = "my father died and I am the executor of the estate"
    pr = predict(built["department"]["model"], text)
    assert pr.top_words and all(w.split()[0] in text for w in pr.top_words)


def test_even_mix_is_below_threshold(built, cfg):
    t = ("Someone made payments on my card that I did not make. "
         "My father died last month and I am dealing with the estate.")
    pr = predict(built["department"]["model"], t)
    assert pr.confidence < cfg["routing_threshold"], pr


def test_nonsense_type_is_other_or_unsure(built):
    pr = predict(built["type"]["model"], "zzyzx plugh quux frobnicate")
    assert pr.label == "Other" or pr.confidence < 0.45


def test_predict_is_fast(built):
    m = built["department"]["model"]
    t0 = time.perf_counter()
    for _ in range(50):
        predict(m, "I was charged an overdraft fee that I was never told about.")
    assert (time.perf_counter() - t0) / 50 < 0.02


def test_train_returns_pipeline():
    m = train(["red apple", "blue sky", "red rose", "blue sea"], ["x", "y", "x", "y"])
    assert predict(m, "red").label == "x"


def test_looks_english():
    assert looks_english("I want to make a complaint about the charge on my account.")
    assert not looks_english("Je voudrais faire une réclamation concernant les frais sur mon compte bancaire.")
    assert looks_english("Help me")  # under 5 words skips the check
