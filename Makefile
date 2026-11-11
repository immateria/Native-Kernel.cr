CRYSTAL ?= crystal

.PHONY: check format native
check:
	$(CRYSTAL) tool format --check src spec scripts
	$(CRYSTAL) spec --error-on-warnings
ifeq ($(shell uname -s),Darwin)
	CRYSTAL=$(CRYSTAL) $(CRYSTAL) run scripts/check-native.cr -- $(RECEIPTS)
endif

format:
	$(CRYSTAL) tool format src spec scripts

native:
	CRYSTAL=$(CRYSTAL) $(CRYSTAL) run scripts/check-native.cr -- $(RECEIPTS)
