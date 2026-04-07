Feature: koffee Exceptions

    Scenario Outline: User inputs an invalid video file
        Given a user has a basic Korean video file
        But the user corrupts the file somehow
        When the user calls the koffee API
        Then the user receives the error message <message>

    Examples: message
        | message                                                    |
        | Input file is not valid or does not exist. |
