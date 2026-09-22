import unittest
from unittest.mock import MagicMock, patch
import datetime
import pytz

from TutoringCalculator.apis.drive_sheets_api import (
    parse_hours,
    parse_currency,
    is_valid_student_name,
    update_sheet_pay_status,
    update_sheet_hours_and_balances,
    get_previous_balances
)
from TutoringCalculator.apis.calendar_api import calculate_tutoring_hours
from TutoringCalculator.config import PST


class TestTutoringCalculator(unittest.TestCase):

    def test_parse_hours(self):
        self.assertEqual(parse_hours(None), 0.0)
        self.assertEqual(parse_hours(""), 0.0)
        self.assertEqual(parse_hours(0), 0.0)
        self.assertEqual(parse_hours("0"), 0.0)
        self.assertEqual(parse_hours("0.0"), 0.0)
        self.assertEqual(parse_hours(1.5), 1.5)
        self.assertEqual(parse_hours("1.5"), 1.5)
        self.assertEqual(parse_hours(" 2.75 hrs "), 2.75)

    def test_get_previous_balances_status_matching(self):
        """Ensures get_previous_balances recognizes both 'Need to Pay' and 'Not Paid'."""
        mock_creds = MagicMock()
        mock_sheets_svc = MagicMock()
        mock_drive_svc = MagicMock()

        with patch('TutoringCalculator.apis.drive_sheets_api.get_drive_service', return_value=mock_drive_svc), \
             patch('TutoringCalculator.apis.drive_sheets_api.get_sheets_service', return_value=mock_sheets_svc), \
             patch('TutoringCalculator.apis.drive_sheets_api.get_or_create_year_folder', return_value='folder_123'):

            mock_drive_svc.files().list().execute.return_value = {
                'files': [{'id': 'prev_sheet_id', 'name': '09.07.26 - 09.13.26 CALCULATED'}]
            }

            # Row columns: [Status, Student Name, Hours, Rate, Subtotal, PrevBal, TotalBalance]
            mock_sheets_svc.spreadsheets().values().get().execute.return_value = {
                'values': [
                    ['Need to Pay', 'Elijah Dinh', '2', '$60', '$120', '$0', '$120.00'],
                    ['Not Paid', 'Ellie Hoang', '1', '$60', '$60', '$0', '$60.00'],
                    ['Paid', 'Michael Brower', '3', '$60', '$180', '$0', '$0.00'],
                    ['', 'Amelie Meeker', '0', '$60', '$0', '$0', '$0.00'],
                ]
            }

            balances = get_previous_balances(mock_creds, "09.14.26", "09.20.26")
            self.assertEqual(balances.get('Elijah Dinh'), 120.0)
            self.assertEqual(balances.get('Elijah'), 120.0)
            self.assertEqual(balances.get('Ellie Hoang'), 60.0)
            self.assertEqual(balances.get('Ellie'), 60.0)
            self.assertNotIn('Michael Brower', balances)
            self.assertNotIn('Amelie Meeker', balances)

    def test_update_sheet_pay_status_hours_zero_not_marked(self):
        """Verifies that if hours = 0, status is NOT marked as Need to Pay / Not Paid."""
        mock_creds = MagicMock()
        mock_sheets_svc = MagicMock()

        with patch('TutoringCalculator.apis.drive_sheets_api.get_sheets_service', return_value=mock_sheets_svc):
            # Row index starts at 5:
            # Row 5: Elijah - 2.0 hrs, blank status -> should become 'Need to Pay'
            # Row 6: Ellie - 0.0 hrs, blank status -> should STAY blank (not marked)
            # Row 7: Michael - 0.0 hrs, previously marked 'Need to Pay' -> should be CLEARED
            # Row 8: Amelie - 0.0 hrs, previously marked 'Not Paid' -> should be CLEARED
            # Row 9: Jack - 3.0 hrs, already 'Paid' -> untouched
            mock_sheets_svc.spreadsheets().values().get().execute.return_value = {
                'values': [
                    ['', 'Elijah Dinh', '2.0'],
                    ['', 'Ellie Hoang', '0.0'],
                    ['Need to Pay', 'Michael Brower', '0'],
                    ['Not Paid', 'Amelie Meeker', '0.0'],
                    ['Paid', 'Jack Glandorf', '3.0']
                ]
            }

            batch_update_mock = mock_sheets_svc.spreadsheets().values().batchUpdate()
            batch_update_mock.execute.return_value = {}

            res = update_sheet_pay_status(mock_creds, 'test_sheet_id')
            self.assertEqual(res['status'], 'success')

            # Inspect the batch update payload
            call_args = mock_sheets_svc.spreadsheets().values().batchUpdate.call_args
            self.assertIsNotNone(call_args)
            body = call_args[1].get('body') or call_args[0][0]
            updates = body.get('data', [])

            # Row 5 (Elijah, hrs > 0, blank) -> 'Need to Pay'
            # Row 7 (Michael, hrs == 0, 'Need to Pay') -> cleared ''
            # Row 8 (Amelie, hrs == 0, 'Not Paid') -> cleared ''
            # Row 6 (Ellie, hrs == 0, blank) -> MUST NOT BE in updates!
            updates_by_range = {u['range']: u['values'][0][0] for u in updates}

            self.assertEqual(updates_by_range.get('B5'), 'Need to Pay')
            self.assertNotIn('B6', updates_by_range, "Ellie (0 hrs, blank) should not be marked as Need to Pay")
            self.assertEqual(updates_by_range.get('B7'), '', "Michael (0 hrs, pre-existing Need to Pay) should be cleared")
            self.assertEqual(updates_by_range.get('B8'), '', "Amelie (0 hrs, pre-existing Not Paid) should be cleared")
            self.assertNotIn('B9', updates_by_range, "Jack (already Paid) should not be modified")

    def test_update_sheet_hours_and_balances_clears_zero_hour_status(self):
        """Verifies update_sheet_hours_and_balances clears status for 0-hour students if previously marked."""
        mock_creds = MagicMock()
        mock_sheets_svc = MagicMock()

        with patch('TutoringCalculator.apis.drive_sheets_api.get_sheets_service', return_value=mock_sheets_svc):
            # student_rows read from B5:C
            # Row 5: Elijah - status 'Need to Pay', 2.0 hrs
            # Row 6: Ellie - status 'Need to Pay', 0.0 hrs -> should clear B6
            # Row 7: Michael - status '', 0.0 hrs -> remains ''
            mock_sheets_svc.spreadsheets().values().get().execute.side_effect = [
                # First get for B5:C
                {
                    'values': [
                        ['Need to Pay', 'Elijah Dinh'],
                        ['Need to Pay', 'Ellie Hoang'],
                        ['', 'Michael Brower'],
                    ]
                },
                # Second get for FORMATTED_VALUE C5:H7
                {
                    'values': [
                        ['Elijah Dinh', '2.0', '$60', '$120.00', '$0.00', '$120.00'],
                        ['Ellie Hoang', '0.0', '$60', '$0.00', '$0.00', '$0.00'],
                        ['Michael Brower', '0.0', '$60', '$0.00', '$0.00', '$0.00'],
                    ]
                },
                # Third get for H summary
                {'values': [['$120.00']]}
            ]

            mock_sheets_svc.spreadsheets().values().batchUpdate().execute.return_value = {}

            hours_by_student = {'Elijah Dinh': 2.0, 'Ellie Hoang': 0.0, 'Michael Brower': 0.0}
            prev_balances = {}

            res = update_sheet_hours_and_balances(mock_creds, 'test_sheet', hours_by_student, prev_balances)
            self.assertEqual(res['status'], 'success')

            call_args = mock_sheets_svc.spreadsheets().values().batchUpdate.call_args
            body = call_args[1].get('body') or call_args[0][0]
            updates = body.get('data', [])

            updates_by_range = {u['range']: u['values'] for u in updates}
            # Column D (hours) and G (balance) updated
            self.assertIn('D5:D7', updates_by_range)
            self.assertIn('G5:G7', updates_by_range)
            # B6 (Ellie, 0 hrs, had 'Need to Pay') should be cleared
            self.assertIn('B6', updates_by_range)
            self.assertEqual(updates_by_range['B6'], [['']])
            # B5 (Elijah, 2 hrs) and B7 (Michael, already blank) should NOT have status clear updates
            self.assertNotIn('B5', updates_by_range)
            self.assertNotIn('B7', updates_by_range)

    def test_calendar_hours_sunday_to_monday_spanning_event(self):
        """
        Tests the boundary condition:
        An event starts Sunday night at 23:00 PST and ends Monday morning at 01:00 PST.
        - Week 1 (Mon 09.14 - Sun 09.20): MUST count the event (start time is Sun 23:00 <= range_end).
        - Week 2 (Mon 09.21 - Sun 09.27): MUST EXCLUDE the event (start time is Sun 23:00 < range_start).
        """
        mock_creds = MagicMock()
        mock_cal_svc = MagicMock()

        spanning_event = {
            'summary': 'Elijah Tutoring',
            'colorId': None,
            # Sunday 2026-09-20 23:00:00 PST to Monday 2026-09-21 01:00:00 PST
            'start': {'dateTime': '2026-09-20T23:00:00-07:00'},
            'end': {'dateTime': '2026-09-21T01:00:00-07:00'}
        }

        monday_event = {
            'summary': 'Ellie Tutoring',
            'colorId': None,
            # Monday 2026-09-21 16:00:00 PST to 17:30:00 PST (1.5 hrs)
            'start': {'dateTime': '2026-09-21T16:00:00-07:00'},
            'end': {'dateTime': '2026-09-21T17:30:00-07:00'}
        }

        with patch('TutoringCalculator.apis.calendar_api.get_calendar_service', return_value=mock_cal_svc), \
             patch('TutoringCalculator.apis.calendar_api.resolve_calendar_id', return_value='cal_123'):

            # Test Week 1: Mon 09.14.26 to Sun 09.20.26
            # Google Calendar API returns spanning_event because it overlaps
            mock_cal_svc.events().list().execute.return_value = {
                'items': [spanning_event]
            }
            week1_hours = calculate_tutoring_hours(
                mock_creds, "09.14.26", "09.20.26",
                sheet_student_names=['Elijah Dinh', 'Ellie Hoang']
            )
            # Spanning event started on Sunday 09.20, so it belongs to Week 1 (2.0 hrs)
            self.assertEqual(week1_hours.get('Elijah Dinh'), 2.0)
            self.assertEqual(week1_hours.get('Elijah'), 2.0)

            # Test Week 2: Mon 09.21.26 to Sun 09.27.26
            # Google Calendar API returns spanning_event (ended Monday 01:00 > timeMin) AND monday_event
            mock_cal_svc.events().list().execute.return_value = {
                'items': [spanning_event, monday_event]
            }
            week2_hours = calculate_tutoring_hours(
                mock_creds, "09.21.26", "09.27.26",
                sheet_student_names=['Elijah Dinh', 'Ellie Hoang']
            )
            # Spanning event MUST BE EXCLUDED from Week 2 because its start time is before Monday 00:00 PST!
            self.assertNotIn('Elijah Dinh', week2_hours, "Spanning event should not be double-counted in Week 2")
            self.assertNotIn('Elijah', week2_hours)
            # Monday event must be included
            self.assertEqual(week2_hours.get('Ellie Hoang'), 1.5)
            self.assertEqual(week2_hours.get('Ellie'), 1.5)


if __name__ == '__main__':
    unittest.main()
