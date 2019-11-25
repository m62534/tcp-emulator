#!/usr/bin/python3

counter = 0

dataArray = [1, 2, 3, 4, 5, 6, 7, 8, 9]

# initial
windowSize = 3
slidingWindow = []
while len(slidingWindow) < windowSize:
    
    slidingWindow.append(dataArray[counter])
    counter = counter + 1

print("initial window: ", slidingWindow)

# If first element of window received, pop it.
received  = True

if received and not len(slidingWindow) == 0:
    slidingWindow.pop(0)
    if dataArray[counter]:
        slidingWindow.append(dataArray[counter])



print("After Pop: ", slidingWindow)