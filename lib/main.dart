import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:geolocator/geolocator.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'eKurier Agent',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final FlutterTts flutterTts = FlutterTts();
  bool isLoading = false;
  String latestLoadInfo =
      "اضغط على الزر أدناه لجلب وفلترة أحسن الحمولات لسيارتك";

  @override
  void initState() {
    super.initState();
    _initTts();
  }

  void _initTts() async {
    await flutterTts.setLanguage("ar-SA");
    await flutterTts.setSpeechRate(0.42);
    await flutterTts.setPitch(1.0);
  }

  // دالة جلب موقع الـ GPS الحالي لحارث
  Future<Position?> _getCurrentLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('يرجى تفعيل خدمة الـ GPS على الهاتف')),
      );
      return null;
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم رفض صلاحية الوصول للموقع')),
        );
        return null;
      }
    }

    return await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }

  // دالة تأكيد الطلب وترجيع الموقع للوكيل
  void _confirmOrderAndSend() async {
    setState(() {
      isLoading = true;
    });

    Position? position = await _getCurrentLocation();

    if (position != null) {
      String gpsCoords =
          "Lat: ${position.latitude}, Long: ${position.longitude}";

      setState(() {
        latestLoadInfo =
            "تم التقاط الموقع بنجاح:\n$gpsCoords\nجاري إرسال التأكيد عبر وكيل البريد...";
      });

      // نطق الرسالة لحارث
      await flutterTts.speak("تم التقاط موقعك بنجاح، جاري تأكيد الطلب");

      // هنا يتم توجيه الطلب إلى وكيل الإيميلات المحلي أو إرساله فوراً
    }

    setState(() {
      isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('مساعد e-kurier الذكي'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              latestLoadInfo,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 30),
            isLoading
                ? const CircularProgressIndicator()
                : ElevatedButton.icon(
                    onPressed: _confirmOrderAndSend,
                    icon: const Icon(Icons.location_on),
                    label: const Text('تأكيد الطلب وجلب الموقع'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 14,
                      ),
                      textStyle: const TextStyle(fontSize: 18),
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}
