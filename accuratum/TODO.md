## Accuratum Sundial

I: For a given date, write a function that finds the previous and next solstice (considering only year, month, day).
If the date specified if is a solstice, the current solstice is the previous, only calculate the next solstice;

II: Write a datetime series with these solstices at the edges, with elements separated, at least by a certain
number of specified days;

III: Create a frame of reference on Earth in a certain specified latitude and longitude;

IVa:  Calculate the sun_rise at the frame defined on task III for each element in the serie specified on task II.
Add one hour to these elements.

IVb: Calculate the sun_set at the frame defined on task III for each element in the serie specified on task II. Subtract one our to these elements.

V: For each pair (sun_set, sun_rise) which is bigger than 2h, create a time series starting on sun_rise +1h and ending
on sun_set-1h, separated by one minute. Precisions must be only up to minutes, only

VI: Create a 2D NDArray object (or a vector structure) with the elements on the previous elements.

VII: Calculate the sun position for each element in the data structure created on task VI;

VIII: Given the length of a certain plumb as plumb_length, calculate the shadow of the tip of the plumb for each element on task VII.

IX: Save this data into a file (think better on which data to save).

X: Plot x,y lines of the shadows obtained on task VIII; save this image on a file named


## Ideas for later.

- test whether ephem works with python 3.13, 3.14rc
- test