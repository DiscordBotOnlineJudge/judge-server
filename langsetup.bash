#!/bin/sh
sudo apt-get install git

cd
sudo apt install -y curl

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
sudo apt-get install default-jdk -y
sudo apt-get install build-essential -y
sudo apt-get install ruby -y
sudo apt-get install fpc -y
curl -fsSL https://deb.nodesource.com/setup_17.x | sudo -E bash -
sudo apt install -y nodejs  
sudo npm install coffeescript
cd
git clone https://github.com/BattleMage0231/rickroll.git
cd rickroll
cargo build --release
sudo cp target/release/rickroll /usr/bin/rickroll
sudo npm install -g typescript
sudo npm i --save-dev @types/node
cd
git clone https://github.com/philburk/pforth.git
cd pforth
sudo cmake .
sudo make
cd fth
sudo cp pforth_standalone /usr/bin/pforth
cd