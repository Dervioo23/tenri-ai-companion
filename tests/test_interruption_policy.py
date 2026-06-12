from app.services.interruption_policy import InterruptionPolicy


class TestCanInterrupt:
    def test_can_interrupt_initially(self):
        assert InterruptionPolicy().can_interrupt()

    def test_cannot_interrupt_when_disabled(self):
        assert not InterruptionPolicy(enabled=False).can_interrupt()

    def test_cooldown_blocks_after_record(self):
        policy = InterruptionPolicy(cooldown_seconds=90)
        policy.record_interruption()
        assert not policy.can_interrupt()

    def test_can_interrupt_after_zero_cooldown(self):
        policy = InterruptionPolicy(cooldown_seconds=0)
        policy.record_interruption()
        assert policy.can_interrupt()

    def test_max_per_session_blocks_further(self):
        policy = InterruptionPolicy(max_per_session=2, cooldown_seconds=0)
        policy.record_interruption()
        policy.record_interruption()
        assert not policy.can_interrupt()

    def test_session_count_increments(self):
        policy = InterruptionPolicy(cooldown_seconds=0)
        policy.record_interruption()
        policy.record_interruption()
        assert policy._session_count == 2

    def test_seconds_until_next_zero_initially(self):
        assert InterruptionPolicy().seconds_until_next() == 0.0

    def test_seconds_until_next_positive_after_record(self):
        policy = InterruptionPolicy(cooldown_seconds=90)
        policy.record_interruption()
        remaining = policy.seconds_until_next()
        assert 88.0 < remaining <= 90.0

    def test_seconds_until_next_zero_after_zero_cooldown(self):
        policy = InterruptionPolicy(cooldown_seconds=0)
        policy.record_interruption()
        assert policy.seconds_until_next() == 0.0


class TestSuggestMode:
    def test_slide_change_returns_comment(self):
        assert InterruptionPolicy().suggest_mode("slide_change") == "comment"

    def test_slide_change_with_notes_returns_correction(self):
        assert InterruptionPolicy().suggest_mode("slide_change_with_notes") == "correction"

    def test_audience_increase_returns_question(self):
        assert InterruptionPolicy().suggest_mode("audience_increase") == "question"

    def test_audience_decrease_returns_comment(self):
        assert InterruptionPolicy().suggest_mode("audience_decrease") == "comment"

    def test_unknown_trigger_falls_back_to_comment(self):
        assert InterruptionPolicy().suggest_mode("unknown_event") == "comment"


class TestBuildPrompt:
    def test_comment_includes_slide_title(self):
        slide = {"title": "La Galigo", "presenter_notes": ""}
        prompt = InterruptionPolicy().build_prompt("comment", slide)
        assert "La Galigo" in prompt

    def test_question_references_slide_title(self):
        slide = {"title": "Pembukaan", "presenter_notes": ""}
        prompt = InterruptionPolicy().build_prompt("question", slide)
        assert "Pembukaan" in prompt

    def test_correction_includes_presenter_notes(self):
        slide = {"title": "Slide", "presenter_notes": "Jangan lupa demo!"}
        prompt = InterruptionPolicy().build_prompt("correction", slide)
        assert "Jangan lupa demo!" in prompt

    def test_correction_without_notes_uses_title(self):
        slide = {"title": "Arsitektur", "presenter_notes": ""}
        prompt = InterruptionPolicy().build_prompt("correction", slide)
        assert "Arsitektur" in prompt

    def test_memory_includes_slide_title(self):
        slide = {"title": "Arsitektur Sistem", "presenter_notes": ""}
        prompt = InterruptionPolicy().build_prompt("memory", slide)
        assert "Arsitektur Sistem" in prompt

    def test_fallback_when_no_slide(self):
        prompt = InterruptionPolicy().build_prompt("comment", None)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_unknown_mode_returns_string(self):
        slide = {"title": "Test", "presenter_notes": ""}
        prompt = InterruptionPolicy().build_prompt("xyz", slide)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_all_modes_return_non_empty(self):
        policy = InterruptionPolicy()
        slide = {"title": "Judul", "presenter_notes": "Catatan penting."}
        for mode in ("comment", "question", "correction", "memory"):
            result = policy.build_prompt(mode, slide)
            assert result, f"mode '{mode}' returned empty string"


class TestPerTriggerCooldown:
    def test_can_interrupt_trigger_initially(self):
        policy = InterruptionPolicy()
        assert policy.can_interrupt_trigger("t001", 90)

    def test_cannot_interrupt_after_record(self):
        policy = InterruptionPolicy()
        policy.record_trigger_interruption("t001")
        assert not policy.can_interrupt_trigger("t001", 90)

    def test_can_interrupt_after_zero_cooldown(self):
        policy = InterruptionPolicy()
        policy.record_trigger_interruption("t001")
        assert policy.can_interrupt_trigger("t001", 0)

    def test_different_triggers_independent(self):
        policy = InterruptionPolicy()
        policy.record_trigger_interruption("t001")
        # t002 has not been fired — should still be allowed
        assert policy.can_interrupt_trigger("t002", 90)

    def test_session_count_increments_on_trigger(self):
        policy = InterruptionPolicy(cooldown_seconds=0)
        policy.record_trigger_interruption("t001")
        policy.record_trigger_interruption("t002")
        assert policy._session_count == 2

    def test_max_per_session_blocks_trigger(self):
        policy = InterruptionPolicy(max_per_session=2, cooldown_seconds=0)
        policy.record_trigger_interruption("t001")
        policy.record_trigger_interruption("t002")
        assert not policy.can_interrupt_trigger("t003", 0)

    def test_disabled_policy_blocks_trigger(self):
        policy = InterruptionPolicy(enabled=False)
        assert not policy.can_interrupt_trigger("t001", 0)

    def test_trigger_cooldown_independent_of_global(self):
        policy = InterruptionPolicy(cooldown_seconds=90)
        # Fire a global interruption (slide advance)
        policy.record_interruption()
        # Global cooldown blocks can_interrupt()
        assert not policy.can_interrupt()
        # But a trigger with short cooldown should use its own timer
        assert policy.can_interrupt_trigger("t001", 0)
