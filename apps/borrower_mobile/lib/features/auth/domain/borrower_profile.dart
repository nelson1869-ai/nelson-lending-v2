class BorrowerProfile {
  final String borrowerId;
  final String accountId;
  final String firstName;
  final String lastName;
  final String phoneNumber;
  final String accountStatus;

  const BorrowerProfile({
    required this.borrowerId,
    required this.accountId,
    required this.firstName,
    required this.lastName,
    required this.phoneNumber,
    required this.accountStatus,
  });

  factory BorrowerProfile.fromJson(Map<String, dynamic> json) {
    return BorrowerProfile(
      borrowerId:
          json['borrowerId'] as String? ?? json['borrower_id'] as String,
      accountId: json['accountId'] as String? ?? json['account_id'] as String,
      firstName: json['firstName'] as String? ?? json['first_name'] as String,
      lastName: json['lastName'] as String? ?? json['last_name'] as String,
      phoneNumber:
          json['phoneNumber'] as String? ?? json['phone_number'] as String,
      accountStatus:
          json['accountStatus'] as String? ?? json['account_status'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
        'borrowerId': borrowerId,
        'accountId': accountId,
        'firstName': firstName,
        'lastName': lastName,
        'phoneNumber': phoneNumber,
        'accountStatus': accountStatus,
      };

  String get fullName => '$firstName $lastName'.trim();
}
