class OwnerBorrowerModel {
  final String id;
  final String firstName;
  final String lastName;
  final String nationalId;
  final String phoneNumber;
  final String status;

  const OwnerBorrowerModel({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.nationalId,
    required this.phoneNumber,
    required this.status,
  });

  factory OwnerBorrowerModel.fromJson(Map<String, dynamic> json) => OwnerBorrowerModel(
        id: json['id'] as String,
        firstName: json['firstName'] as String,
        lastName: json['lastName'] as String,
        nationalId: json['nationalId'] as String,
        phoneNumber: json['phoneNumber'] as String,
        status: json['status'] as String,
      );

  String get fullName => '$firstName $lastName';
}
