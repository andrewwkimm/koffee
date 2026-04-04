Feature: koffee APIs

    Scenario Outline: User gets a translated subtitle file
        Given a user has a basic <language> video file
        And the user sets the output directory to <path>
        When the user calls the koffee API
        Then the user receives a subtitle file

    Examples: language
        | language | path        |
        | Korean   | scratch/tmp |
        | Japanese | scratch/tmp |