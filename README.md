# Alpaca Spindl
A python based platform for designing, back testing, and running trading strategies utilizing the alpaca brokerage

# Installation
`docker build . -t alpaca_spindl:1.0`

`docker run -ti -p 15000:15000  alpaca_spindl:1.0`


**Q&A**

**What does Spindl stand for?**

Slayton's Platform (for) Investment (via) Nonmanual Daytrading and Logging

**What kind of developer puts their first name in the acronym of their product?**

The kind that wants to make it very clear that this is not a commercially viable program, but at best, a starting point for your own project.

**Are you sure I can’t immediately deploy this for personal/commercial use?**

This software is open source, so yes, you can do whatever you want with it. However I highly, highly recommend against tying it to your personal finances as is, or God forbid, trying to implement it in prod at your company. The strategies I've included are _not_ viable in the long term, and this is meant entirely as a platform for other traders to develop their own methods.

**How much do you make with this thing?**

Trading the default stocks daily at 25% of our buying power, I average about 50$ per day. I've gained considerably more in the past using riskier methods, but then I've also lost considerably more. Even a trickle can fill a lake if it's steady. The worst day of spindl’s history was August 1st, 2024, but you can blame the Yen Carry Trade collapsing for that one. I’ll add anomaly detection in a future release.
