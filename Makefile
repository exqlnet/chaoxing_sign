.PHONY: txscf
txscf:
	mkdir -p .tmp && cp -r ./* ./.tmp
	pip3 install -r ./requirements.txt -i https://pypi.douban.com/simple -t ./.tmp
	zip -r ./cx.zip ./.tmp/*
	rm -rf ./.tmp
