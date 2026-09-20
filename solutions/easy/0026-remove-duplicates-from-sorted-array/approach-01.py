# LeetCode: Remove Duplicates from Sorted Array
# Problem ID: 0026
# Difficulty: Easy
# Language: python
# Approach: 01
# Submission ID: 2134075893
class Solution:
    def removeDuplicates(self, nums):

        if len(nums) == 0:
            return 0

        k = 1

        for i in range(1, len(nums)):

            if nums[i] != nums[i-1]:
                nums[k] = nums[i]
                k += 1

        return k