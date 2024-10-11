# Alpaca Spindl
A python based platform for designing, back testing, and running trading strategies utilizing the alpaca brokerage

![Screenshot from 2024-10-11 13-12-30](https://github.com/user-attachments/assets/d9858641-eec8-40f7-bd1e-9dfc00851eb6)
After creating your account, switch to _paper trading_ and generate your api keys
# Installation
1. **Create your Alpaca Account:** To install spindl, you first need to make an account with the [alpaca](https://alpaca.markets/) brokerage.
2. **Clone the Repo:** Clone the repo into your chosen directory and cd into it.
3. **Add Keys to the Broker.py File:** Open the `./lib/tools/Broker_EDIT.py` file with your text editor of choice, then go to your alpaca account in your browser and switch to _paper trading_. There generate your api keys and copy them into the `Broker_EDIT.py` file in the designated fields of the _paper_api_ method. Once your keys have been added, rename the `Broker_EDIT.py` file to `Broker.py`. The file is in .gitignore, but if you'd rather store the keys in a less risky fashion (especially if your computer is used by multiple users), I'd encourage altering the code for better security.
4. **Build the Container:** With the `Broker.py` file successfully editted with your access keys you can now build the docker file by running `docker build . -t alpaca_spindl` in the spindl directory.
5. **Run the Container:** Once the image is built, run the container with `docker run -ti --volume=${PWD}/logs:/alpaca_spindl/logs -p 10000:10000 alpaca_spindl`. By default trading logs will be stored in the logs folder of your source spindl directory for the sake of persistence in case the container is halted.
6. **Connect to the Container:** Once the image is running you can either connect to the jupyter notebook at `localhost:10000` in your browser, copying in the token from your terminal, or you can ssh into it via your prefered ide. A couple of the windows machines I tested it on had difficulties using VS Code, but the jupyter notebook functioned as expected. I tested an install on up to date versions of ubuntu and debian without issue. I did not test an install on a mac.
7. **Play around with Tuner:** Once connected to the spindl container, open the tuner.ipynb file and try running the cells.

# Q&A

**What does Spindl stand for?**

Slayton's Platform (for) Investment (via) Nonmanual Daytrading and Logging

**What kind of developer puts their first name in the acronym of their product?**

The kind that wants to make it very clear that this is not a commercially viable program, but at best, a starting point for your own projects.

**Are you sure I can’t immediately deploy this for personal/commercial use?**

This software is open source so you can do whatever you want with it, however I highly recommend against using it "out of the box." The strategies I've included are _not_ viable in the long term, and this is meant entirely as a platform for other traders to develop their own methods.

**How much do you make with this thing?**

Trading the default stocks daily at 25% of our buying power, I average about 50$ per day. I've gained considerably more in the past using riskier methods, but then I've also lost considerably more. Even a trickle can fill a lake if it's steady. The worst day of spindl’s history was August 1st, 2024, but you can blame the Yen Carry Trade collapsing for that one. I’ll add anomaly detection in a future release.
