
.PHONY: chapter-tests

chapter-tests:
ifndef chapter
	$(error Missing chapter argument. Usage: make chapter-tests chapter=<num> [stage=<name>])
endif
ifeq ($(origin stage), undefined)
	./writing-a-c-compiler-tests/test_compiler src/compiler_driver --chapter $(chapter)
else
	./writing-a-c-compiler-tests/test_compiler src/compiler_driver --chapter $(chapter) --stage $(stage)
endif

.PHONY: c-test

c-test:
	./src/compiler_driver --$(stage) ./tests/test.c

.PHONY: tests

tests:
	PYTHONPATH=./src pytest tests/

.PHONY coverage:

coverage:
	PYTHONPATH=./src pytest --cov=src --cov-report=term tests/

.PHONY: generate-tests

generate-tests:
ifndef module
	$(error Missing module argument. Usage: make generate-tests module=<module-name>)
endif
	sudo docker run --rm \
		-v "$(PWD)/src":/input \
		-v "$(PWD)/tests":/output \
		-v requirements.txt:/package \
		-e PYTHONPATH=/input \
		pynguin:0.40.0 \
		--project-path /input \
		--module-name $(module) \
		--output-path /output \
		--verbose
